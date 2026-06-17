"""
Attribute Transcripts to VAD Segments

Reads raw full-audio transcripts from data/sarvam_transcripts.json and maps
transcript text to segment WAV chunks based on overlapping timestamps.
"""

import os
import json
from pathlib import Path

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

def attribute_transcripts():
    print("=== Attributing Transcripts to VAD Segments ===")
    
    # Paths
    transcripts_path = ROOT_DIR / "data" / "sarvam_transcripts.json"
    segments_path = ROOT_DIR / "data" / "segments_metadata.jsonl"
    
    if not transcripts_path.exists():
        print(f"Error: Raw transcripts file not found: {transcripts_path}")
        print("Please run step 3 (ASR + Diarization) first.")
        return
        
    if not segments_path.exists():
        print(f"Error: Segments metadata file not found: {segments_path}")
        print("Please run step 2 (VAD Segmentation) first.")
        return
        
    # 1. Load raw transcripts mapping: video_id -> raw_response
    print(f"Loading raw transcripts from: {transcripts_path}")
    with open(transcripts_path, "r", encoding="utf-8") as f:
        sarvam_data = json.load(f)
        
    # 2. Load VAD segments
    print(f"Loading VAD segments from: {segments_path}")
    records = []
    with open(segments_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    total = len(records)
    successful = 0
    failed = 0
    total_chars = 0
    
    # 3. Perform attribution
    print("Mapping transcripts based on overlapping timestamps...")
    for idx, record in enumerate(records, start=1):
        video_id = record.get("video_id")
        seg_start = record.get("start", 0.0)
        seg_end = record.get("end", 0.0)
        
        raw_response = sarvam_data.get(video_id)
        
        if not raw_response:
            # No response cached for this video
            record["transcript"] = ""
            record["language"] = "unknown"
            record["transcription_confidence"] = 0.0
            failed += 1
            continue
            
        # Extract entries from diarized transcript
        entries = []
        if "diarized_transcript" in raw_response:
            entries = raw_response["diarized_transcript"].get("entries", [])
        elif "entries" in raw_response:
            entries = raw_response["entries"]
            
        # Find entries overlapping with this segment's duration
        overlapping_entries = []
        for entry in entries:
            entry_start = float(entry.get("start_time_seconds", 0.0))
            entry_end = float(entry.get("end_time_seconds", 0.0))
            
            # Check overlap: max(start) < min(end)
            overlap_duration = min(seg_end, entry_end) - max(seg_start, entry_start)
            if overlap_duration > 0:
                overlapping_entries.append(entry)
                
        if overlapping_entries:
            # Sort chronologically by start time
            overlapping_entries.sort(key=lambda x: float(x.get("start_time_seconds", 0.0)))
            
            # Concatenate transcripts
            transcript_text = " ".join([
                e.get("transcript", "").strip() 
                for e in overlapping_entries 
                if e.get("transcript", "").strip()
            ]).strip()
            
            # Clean up double spaces
            transcript_text = " ".join(transcript_text.split())
            
            # Set values
            record["transcript"] = transcript_text
            record["language"] = raw_response.get("language_code", "en-IN")
            record["transcription_confidence"] = float(raw_response.get("confidence", 1.0))
            
            total_chars += len(transcript_text)
            successful += 1
        else:
            record["transcript"] = ""
            record["language"] = raw_response.get("language_code", "en-IN")
            record["transcription_confidence"] = 0.0
            failed += 1
            
        if idx % 500 == 0 or idx == total:
            print(f"Processed {idx}/{total} segments...")
            
    # 4. Save updated metadata
    with open(segments_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"\n=== Transcript Attribution Summary ===")
    print(f"Total segments: {total}")
    print(f"Successfully attributed: {successful}")
    print(f"Failed / Empty transcripts: {failed}")
    if successful > 0:
        print(f"Average characters per segment: {total_chars / successful:.1f}")
    print(f"Saved updated segment records to: {segments_path}")

if __name__ == "__main__":
    attribute_transcripts()
