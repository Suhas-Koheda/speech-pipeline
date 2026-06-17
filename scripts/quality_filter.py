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
    "max_clipping_ratio": 0.01,  # max 1% of samples near peak
    "clipping_threshold": 0.95,  # amplitude threshold
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
    clipping_ratio = clipping_samples / len(audio)
    
    is_clipped = (peak > threshold and 
                  clipping_ratio > QUALITY_THRESHOLDS["max_clipping_ratio"])
    
    return is_clipped, clipping_ratio


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
    Calculate quality score (0.0-1.0) for a segment.
    
    Returns:
        Tuple of (quality_score, issues_list)
    """
    issues = []
    score = 1.0
    
    # Check speaker type
    if not check_speaker_type(record.get("dominant_speaker", "UNKNOWN")):
        issues.append(f"INVALID_SPEAKER_{record.get('dominant_speaker')}")
        score = 0.0
    
    # Check transcript
    if not check_transcript(record.get("transcript", "")):
        issues.append("EMPTY_TRANSCRIPT")
        score = 0.0
    
    # Check duration
    duration = record.get("duration", 0)
    if not check_duration(duration):
        issues.append(f"INVALID_DURATION_{duration:.2f}s")
        score = 0.0
    
    # Skip audio-based checks if score is already 0
    if score > 0:
        try:
            # Load audio segment
            audio, sr = sf.read(audio_path)
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            
            # Check for clipping
            is_clipped, clipping_ratio = detect_audio_clipping(
                audio,
                QUALITY_THRESHOLDS["clipping_threshold"]
            )
            
            if is_clipped:
                issues.append(f"CLIPPED_AUDIO_{clipping_ratio:.3f}")
                score *= 0.5
            
            # Check noise level
            noise_level = estimate_noise_level(audio, sr)
            
            if noise_level > QUALITY_THRESHOLDS["max_noise_level"]:
                issues.append(f"HIGH_NOISE_{noise_level:.1f}dB")
                score *= 0.7
        
        except Exception as e:
            print(f"Error checking audio quality for {audio_path}: {e}")
            issues.append("AUDIO_READ_ERROR")
            score = 0.0
    
    return score, issues


def apply_quality_filters(
    input_path="../data/segments_metadata.jsonl",
    output_path="../data/segments_metadata_filtered.jsonl",
):
    """
    Apply quality filters to all segments.
    
    Reads original segments, calculates quality scores, and writes
    both original records (with quality scores) and filtered records.
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
            
            # Add to filtered set if high quality
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
    
    # Write updated metadata (all records with quality scores)
    with open(input_path, "w", encoding="utf-8") as f:
        for record in updated_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Write filtered metadata (only high-quality records)
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


if __name__ == "__main__":
    apply_quality_filters()
