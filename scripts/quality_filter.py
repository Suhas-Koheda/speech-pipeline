"""
Quality Filtering Pipeline

Removes low-quality segments based on:
- Speaker type (MIXED, UNKNOWN)
- Audio clipping detection
- Duration constraints (3.0s - 20.0s)
- Background noise estimation
- Empty / too short transcripts
"""

import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

# Quality filter thresholds
QUALITY_THRESHOLDS = {
    "min_duration": 3.0,  # seconds (from User Request)
    "max_duration": 20.0,  # seconds
    "min_transcript_len": 5,  # characters
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
    """
    try:
        f, t, Zxx = signal.stft(audio, sr, nperseg=512)
        mag_spec = np.abs(Zxx)
        frame_energy = 20 * np.log10(np.mean(mag_spec, axis=0) + 1e-10)
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

def calculate_quality_issues(record, audio_path):
    """
    Identify quality issues for a segment.
    Returns a list of issue strings. Empty list = passed.
    speaker_purity_score = dominant_speaker_duration / segment_duration
      (real measurement, preserved).
    """
    issues = []
    
    # Speaker checks
    dominant_speaker = record.get("dominant_speaker", "UNKNOWN")
    speaker = record.get("speaker", "unknown")
    
    if dominant_speaker == "MIXED":
        issues.append("MIXED_SPEAKER")
    elif dominant_speaker == "UNKNOWN" or not speaker or speaker == "unknown" or speaker.lower() == "speaker_unknown":
        issues.append("UNKNOWN_SPEAKER")
    
    # 2. Duration check
    segment_duration = record.get("duration", 0.0)
    if segment_duration <= 0.0:
        segment_duration = record.get("end", 0.0) - record.get("start", 0.0)
        
    if not check_duration(segment_duration):
        issues.append(f"INVALID_DURATION_{segment_duration:.2f}s")
        
    # 3. Transcript check
    transcript = record.get("transcript", "")
    if not isinstance(transcript, str) or not transcript.strip():
        issues.append("EMPTY_TRANSCRIPT")
    elif len(transcript.strip()) < QUALITY_THRESHOLDS["min_transcript_len"]:
        issues.append(f"SHORT_TRANSCRIPT_{len(transcript.strip())}")
        
    # 5. Audio quality checks
    try:
        # Resolve audio_path to absolute
        if isinstance(audio_path, str) and audio_path.startswith("../"):
            abs_audio_path = ROOT_DIR / audio_path.replace("../", "")
        else:
            abs_audio_path = Path(audio_path)
            
        if not abs_audio_path.exists():
            issues.append("AUDIO_NOT_FOUND")
        else:
            audio, sr = sf.read(abs_audio_path)
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
                
            if len(audio) == 0:
                issues.append("EMPTY_AUDIO")
            else:
                is_clipped, clipping_ratio = detect_audio_clipping(
                    audio,
                    QUALITY_THRESHOLDS["clipping_threshold"]
                )
                if is_clipped:
                    issues.append(f"CLIPPED_AUDIO_{clipping_ratio:.3f}")
                    
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

    return issues

def apply_quality_filters(input_path=None, output_path=None):
    """
    Apply quality filters to all segments.
    """
    if input_path is None:
        input_path = ROOT_DIR / "data" / "segments_metadata.jsonl"
    else:
        input_path = Path(input_path)
        
    if output_path is None:
        output_path = ROOT_DIR / "data" / "segments_metadata_filtered.jsonl"
    else:
        output_path = Path(output_path)
        
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        return 0, 0, 0
        
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    total = len(records)
    passed = 0
    failed = 0
    
    print("\n=== Quality Filtering ===")
    print(f"Processing {total} segments...")
    
    filtered_records = []
    updated_records = []
    
    for idx, record in enumerate(records, start=1):
        try:
            audio_path = record.get("segment_path", "")
            
            # Identify quality issues (real measurements only — no quality_score field)
            issues = calculate_quality_issues(record, audio_path)
            record["quality_issues"] = issues
            
            updated_records.append(record)
            
            if not issues:
                filtered_records.append(record)
                passed += 1
            else:
                failed += 1
            
            if idx % 500 == 0 or idx == total:
                print(f"[{idx}/{total}] Processed | Passed: {passed} | Failed: {failed}")
        
        except Exception as e:
            print(f"Error processing segment {idx}: {e}")
            record["quality_issues"] = ["PROCESSING_ERROR"]
            updated_records.append(record)
            failed += 1
            
    # Write updated metadata back to input
    with open(input_path, "w", encoding="utf-8") as f:
        for record in updated_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    # Write filtered metadata
    with open(output_path, "w", encoding="utf-8") as f:
        for record in filtered_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"\n=== Quality Filter Summary ===")
    print(f"Total segments: {total}")
    print(f"Passed quality check: {passed}")
    print(f"Failed quality check: {failed}")
    print(f"Pass rate: {100*passed/total:.1f}%" if total > 0 else "0.0%")
    print(f"\nUpdated: {input_path}")
    print(f"Filtered: {output_path}")
    
    return passed, failed, total

def main():
    input_path = ROOT_DIR / "data" / "segments_metadata.jsonl"
    apply_quality_filters(input_path=input_path)

# if __name__ == "__main__":
#     main()
