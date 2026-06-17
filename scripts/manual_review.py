"""
Manual Review Workflow

Generates a CSV file for human annotation with columns:
- segment_path
- transcript
- emotion
- accepted (empty, to be filled by annotator)
- rejection_reason (empty, to be filled by annotator)

After annotation, filters segments based on human decisions.
"""

import json
import csv
from pathlib import Path
from datetime import datetime


def generate_review_csv(
    input_path="../data/segments_metadata_emotions.jsonl",
    output_csv="../data/review.csv",
):
    """
    Generate CSV file for manual review.
    
    Args:
        input_path: Path to segments metadata with emotions
        output_csv: Path to save review CSV
    """
    records = []
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    except FileNotFoundError:
        print(f"Input file not found: {input_path}")
        return
    
    total = len(records)
    
    if total == 0:
        print("No records found!")
        return
    
    print(f"\n=== Generating Review CSV ===")
    print(f"Total segments: {total}")
    
    # Create CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "segment_path",
                "transcript",
                "emotion",
                "duration",
                "accepted",
                "rejection_reason",
            ],
            extrasaction="ignore"
        )
        
        writer.writeheader()
        
        for record in records:
            writer.writerow({
                "segment_path": record.get("segment_path", ""),
                "transcript": record.get("transcript", "")[:100],  # Truncate long transcripts
                "emotion": record.get("emotion", "neutral"),
                "duration": f"{record.get('duration', 0):.2f}s",
                "accepted": "",  # To be filled by annotator
                "rejection_reason": "",  # To be filled by annotator
            })
    
    print(f"Generated review CSV: {output_csv}")
    print(f"Columns: segment_path, transcript, emotion, duration, accepted, rejection_reason")
    print(f"\nInstructions:")
    print(f"1. Open {output_csv} in Excel or Google Sheets")
    print(f"2. For each row, fill 'accepted' with TRUE or FALSE")
    print(f"3. If FALSE, optionally fill 'rejection_reason' (e.g., 'Poor quality', 'Wrong language')")
    print(f"4. Save the file")
    print(f"5. Run filter_by_acceptance() to create final dataset")


def filter_by_acceptance(
    metadata_path="../data/segments_metadata_emotions.jsonl",
    review_csv="../data/review.csv",
    output_path="../data/segments_metadata_final.jsonl",
):
    """
    Filter segments based on manual review CSV.
    
    Reads annotated review.csv and creates final dataset with only
    accepted segments.
    
    Args:
        metadata_path: Original metadata file
        review_csv: Annotated review CSV
        output_path: Path to save final metadata
    """
    # Load original records
    records_by_path = {}
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                records_by_path[record.get("segment_path", "")] = record
    except FileNotFoundError:
        print(f"Input metadata file not found: {metadata_path}")
        return
    
    # Load review decisions
    accepted_records = []
    rejected_records = []
    total = 0
    
    try:
        with open(review_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total += 1
                segment_path = row.get("segment_path", "").strip()
                accepted_str = row.get("accepted", "").strip().upper()
                rejection_reason = row.get("rejection_reason", "").strip()
                
                # Get original record
                if segment_path not in records_by_path:
                    print(f"Warning: segment not found in metadata: {segment_path}")
                    continue
                
                record = records_by_path[segment_path]
                
                # Check if accepted
                if accepted_str in ["TRUE", "T", "YES", "Y", "1"]:
                    accepted_records.append(record)
                else:
                    record["rejection_reason"] = rejection_reason
                    rejected_records.append(record)
    
    except FileNotFoundError:
        print(f"Review CSV not found: {review_csv}")
        print("Please run generate_review_csv() first")
        return
    
    # Write accepted records
    with open(output_path, "w", encoding="utf-8") as f:
        for record in accepted_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Write rejected records with reasons
    rejected_path = output_path.replace("_final.jsonl", "_rejected.jsonl")
    with open(rejected_path, "w", encoding="utf-8") as f:
        for record in rejected_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"\n=== Manual Review Summary ===")
    print(f"Total rows processed: {total}")
    print(f"Accepted: {len(accepted_records)}")
    print(f"Rejected: {len(rejected_records)}")
    print(f"Acceptance rate: {100*len(accepted_records)/total:.1f}%")
    print(f"\nFinal dataset: {output_path}")
    print(f"Rejected segments: {rejected_path}")


def create_annotation_template(
    metadata_path="../data/segments_metadata_emotions.jsonl",
    output_csv="../data/review_template.csv",
    sample_size=None,
):
    """
    Create a smaller sample CSV for initial annotation testing.
    
    Args:
        metadata_path: Path to segments metadata
        output_csv: Path to save sample CSV
        sample_size: Number of samples to include (None = all)
    """
    records = []
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    except FileNotFoundError:
        print(f"Input file not found: {metadata_path}")
        return
    
    if sample_size and len(records) > sample_size:
        import random
        records = random.sample(records, sample_size)
        print(f"Sampled {sample_size} records from {len(records)} total")
    
    total = len(records)
    
    print(f"\n=== Creating Annotation Template ===")
    print(f"Total segments: {total}")
    
    # Create CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "index",
                "segment_path",
                "transcript",
                "emotion",
                "duration",
                "video_id",
                "channel",
                "accepted",
                "rejection_reason",
                "notes",
            ]
        )
        
        writer.writeheader()
        
        for idx, record in enumerate(records, start=1):
            writer.writerow({
                "index": idx,
                "segment_path": record.get("segment_path", ""),
                "transcript": record.get("transcript", "")[:80],
                "emotion": record.get("emotion", "neutral"),
                "duration": f"{record.get('duration', 0):.2f}s",
                "video_id": record.get("video_id", ""),
                "channel": record.get("channel", ""),
                "accepted": "",
                "rejection_reason": "",
                "notes": "",
            })
    
    print(f"Generated template CSV: {output_csv}")
    print(f"Total rows: {total}")


if __name__ == "__main__":
    print("=== Manual Review Workflow ===\n")
    
    # Step 1: Generate review CSV
    print("Step 1: Generating review CSV...")
    generate_review_csv()
    
    print("\n" + "="*50 + "\n")
    
    # Optionally create template for testing
    print("Step 2: Creating annotation template (sample)...")
    create_annotation_template(sample_size=50)
    
    print("\n" + "="*50 + "\n")
    print("Next steps:")
    print("1. Annotate the review.csv file")
    print("2. Run: python manual_review.py --filter")
    print("   (After implementing command-line arg handling)")
