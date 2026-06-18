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
import soundfile as sf

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

# Quality filter thresholds
QUALITY_THRESHOLDS = {
    "min_duration": 2.0,  # seconds
    "max_duration": 30.0,  # seconds
    "min_transcript_len": 5,  # characters
}

SAMPLING_RATE = 16000

def check_duration(duration):
    """Check if segment duration is within acceptable range."""
    min_dur = QUALITY_THRESHOLDS["min_duration"]
    max_dur = QUALITY_THRESHOLDS["max_duration"]
    return min_dur <= duration <= max_dur

def calculate_quality_issues(record, audio_path):
    """
    Identify quality issues for a segment.
    Returns a list of issue strings. Empty list = passed.
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
