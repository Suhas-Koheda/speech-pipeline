"""
Quality Filtering Pipeline

Removes low-quality segments based on:
- Speaker type (MIXED, UNKNOWN)
- Audio clipping detection
- Duration constraints (5-20 seconds)
- Background noise estimation
- Empty transcripts
"""

import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal


# Quality filter thresholds
QUALITY_THRESHOLDS = {
    "min_duration": 5.0,  # seconds
    "max_duration": 20.0,  # seconds
    "min_speaker_dominance": 0.90,  # 90% dominance
    "min_transcript_len": 5,  # characters
    "min_transcription_confidence": 0.80,  # threshold
    "max_clipping_ratio": 0.01,  # max 1% of samples near peak
    "clipping_threshold": 0.95,  # amplitude threshold
    "silence_db_threshold": -45.0,  # threshold in dB
    "max_silence_ratio": 0.30,  # max 30% of frames can be silence
    "max_noise_level": -40.0,  # dB (approximate)
}

SAMPLING_RATE = 16000


def detect_audio_clipping(audio, threshold=0.95):
    """
    Detect if audio is clipped (peaks near maximum value).
    
    Args:
        audio: Audio samples (numpy array)
        threshold: Amplitude threshold (0-1)
    
    Returns:
        Tuple of (is_clipped, clipping_ratio)
    """
    peak = np.abs(audio).max()
    clipping_samples = np.sum(np.abs(audio) > threshold)
    clipping_ratio = clipping_samples / len(audio) if len(audio) > 0 else 0.0
    
    is_clipped = (peak > threshold and 
                  clipping_ratio > QUALITY_THRESHOLDS["max_clipping_ratio"])
    
    return is_clipped, clipping_ratio


def detect_excessive_silence(audio, threshold_db=-45.0, silence_ratio_threshold=0.30):
    """
    Detect if there is excessive silence in the audio segment.
    """
    try:
        frame_size = 512
        hop_size = 256
        rms = []
        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i+frame_size]
            r = np.sqrt(np.mean(frame**2) + 1e-10)
            rms.append(r)
        
        rms = np.array(rms)
        rms_db = 20 * np.log10(rms)
        
        silent_frames = np.sum(rms_db < threshold_db)
        silence_ratio = silent_frames / len(rms) if len(rms) > 0 else 0.0
        
        return silence_ratio > silence_ratio_threshold, silence_ratio
    except Exception as e:
        print(f"Silence detection error: {e}")
        return False, 0.0


def estimate_noise_level(audio, sr=SAMPLING_RATE):
    """
    Estimate noise level using spectral analysis.
    
    Uses the quietest 10% of frames as noise estimate.
    
    Args:
        audio: Audio samples (numpy array)
        sr: Sampling rate
    
    Returns:
        Noise level estimate (dB)
    """
    try:
        # Compute STFT
        f, t, Zxx = signal.stft(audio, sr, nperseg=512)
        
        # Compute magnitude spectrogram
        mag_spec = np.abs(Zxx)
        
        # Per-frame energy (dB)
        frame_energy = 20 * np.log10(np.mean(mag_spec, axis=0) + 1e-10)
        
        # Use 10th percentile as noise estimate
        noise_level = np.percentile(frame_energy, 10)
        
        return float(noise_level)
    
    except Exception as e:
        print(f"Noise estimation error: {e}")
        return -50.0  # Conservative default


def check_duration(duration):
    """Check if segment duration is within acceptable range."""
    min_dur = QUALITY_THRESHOLDS["min_duration"]
    max_dur = QUALITY_THRESHOLDS["max_duration"]
    
    return min_dur <= duration <= max_dur


def check_speaker_type(dominant_speaker):
    """Check if speaker type is acceptable (not MIXED or UNKNOWN)."""
    return dominant_speaker not in ["MIXED", "UNKNOWN"]


def check_transcript(transcript):
    """Check if transcript is non-empty."""
    return isinstance(transcript, str) and len(transcript.strip()) > 0


def calculate_quality_score(record, audio_path):
    """
    Calculate quality score and identify rejection reasons for a segment.
    
    Returns:
        Tuple of (quality_score, issues_list)
    """
    issues = []
    
    # 1. Speaker checks
    dominant_speaker = record.get("dominant_speaker", "UNKNOWN")
    if dominant_speaker == "MIXED":
        issues.append("MIXED_SPEAKER")
    elif dominant_speaker == "UNKNOWN":
        issues.append("UNKNOWN_SPEAKER")
    
    # Speaker dominance/purity score
    segment_duration = record.get("duration", 0.0)
    if segment_duration <= 0.0:
        segment_duration = record.get("end", 0.0) - record.get("start", 0.0)
        
    speaker_overlap = record.get("speaker_overlap", {})
    if speaker_overlap and dominant_speaker not in ["MIXED", "UNKNOWN"]:
        dominant_overlap = speaker_overlap.get(dominant_speaker, 0.0)
        speaker_purity_score = dominant_overlap / segment_duration if segment_duration > 0 else 0.0
    else:
        speaker_purity_score = 0.0
        
    record["speaker_purity_score"] = round(speaker_purity_score, 3)
    
    if dominant_speaker not in ["MIXED", "UNKNOWN"]:
        if speaker_purity_score < QUALITY_THRESHOLDS["min_speaker_dominance"]:
            issues.append(f"LOW_SPEAKER_DOMINANCE_{speaker_purity_score:.2f}")
            
    # 2. Duration check
    if not check_duration(segment_duration):
        issues.append(f"INVALID_DURATION_{segment_duration:.2f}s")
        
    # 3. Transcript check
    transcript = record.get("transcript", "")
    if not check_transcript(transcript):
        issues.append("EMPTY_TRANSCRIPT")
    elif len(transcript.strip()) < QUALITY_THRESHOLDS["min_transcript_len"]:
        issues.append(f"SHORT_TRANSCRIPT_{len(transcript.strip())}")
        
    # 4. Transcription confidence check
    confidence = record.get("transcription_confidence", 1.0)
    if confidence < QUALITY_THRESHOLDS["min_transcription_confidence"]:
        issues.append(f"LOW_TRANSCRIPTION_CONFIDENCE_{confidence:.2f}")
        
    # 5. Audio quality checks
    try:
        if not Path(audio_path).exists():
            issues.append("AUDIO_NOT_FOUND")
        else:
            audio, sr = sf.read(audio_path)
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
                
            if len(audio) == 0:
                issues.append("EMPTY_AUDIO")
            else:
                # Check for clipping
                is_clipped, clipping_ratio = detect_audio_clipping(
                    audio,
                    QUALITY_THRESHOLDS["clipping_threshold"]
                )
                if is_clipped:
                    issues.append(f"CLIPPED_AUDIO_{clipping_ratio:.3f}")
                    
                # Check excessive silence
                is_silent, silence_ratio = detect_excessive_silence(
                    audio,
                    threshold_db=QUALITY_THRESHOLDS["silence_db_threshold"],
                    silence_ratio_threshold=QUALITY_THRESHOLDS["max_silence_ratio"]
                )
                if is_silent:
                    issues.append(f"EXCESSIVE_SILENCE_{silence_ratio:.2f}")
                    
    except Exception as e:
        print(f"Error checking audio quality for {audio_path}: {e}")
        issues.append("CORRUPTED_AUDIO")

    # Final decision: 1.0 if clean, 0.0 if rejected
    score = 1.0 if not issues else 0.0
    return score, issues


def apply_quality_filters(
    input_path="../data/segments_metadata.jsonl",
    output_path="../data/segments_metadata_filtered.jsonl",
):
    """
    Apply quality filters to all segments.
    """
    records = []
    
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    
    total = len(records)
    passed = 0
    failed = 0
    
    print(f"\n=== Quality Filtering ===")
    print(f"Processing {total} segments...")
    
    filtered_records = []
    updated_records = []
    
    for idx, record in enumerate(records, start=1):
        try:
            audio_path = record.get("segment_path", "")
            
            # Calculate quality score
            score, issues = calculate_quality_score(record, audio_path)
            
            # Update record with quality information
            record["quality_score"] = float(score)
            record["quality_issues"] = issues
            
            updated_records.append(record)
            
            # Add to filtered set if high quality (score == 1.0)
            if score >= 1.0:
                filtered_records.append(record)
                passed += 1
            else:
                failed += 1
            
            if idx % 50 == 0:
                print(f"[{idx}/{total}] Processed | Passed: {passed} | Failed: {failed}")
        
        except Exception as e:
            print(f"Error processing segment {idx}: {e}")
            record["quality_score"] = 0.0
            record["quality_issues"] = ["PROCESSING_ERROR"]
            updated_records.append(record)
            failed += 1
    
    # Write updated metadata (all records with quality scores and issues)
    with open(input_path, "w", encoding="utf-8") as f:
        for record in updated_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Write filtered metadata (only accepted records)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in filtered_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"\n=== Quality Filter Summary ===")
    print(f"Total segments: {total}")
    print(f"Passed quality check: {passed}")
    print(f"Failed quality check: {failed}")
    print(f"Pass rate: {100*passed/total:.1f}%")
    print(f"\nUpdated: {input_path}")
    print(f"Filtered: {output_path}")
    
    return passed, failed, total


def main():
    apply_quality_filters()

# if __name__ == "__main__":
#     main()
