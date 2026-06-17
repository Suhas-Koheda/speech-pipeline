"""
Manual Review Workflow

Generates and filters the dataset based on a manual review CSV.
Columns:
id, video_id, start, end, dominant_speaker, transcript, language, emotion, quality_score, quality_issues, approved, rejection_reason
"""

import json
import csv
import os
from pathlib import Path

def generate_review_csv(
    input_path="../data/segments_metadata_emotions.jsonl",
    output_csv="../data/review.csv",
):
    """
    Generate CSV file for manual review based on the emotion-tagged metadata.
    """
    records = []
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    except FileNotFoundError:
        # Fallback to segments_metadata.jsonl if emotions file doesn't exist yet
        fallback_path = "../data/segments_metadata.jsonl"
        print(f"Input file not found: {input_path}. Trying fallback: {fallback_path}")
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                for line in f:
                    records.append(json.loads(line))
        except FileNotFoundError:
            print("No segments metadata file found. Please run the transcription pipeline first.")
            return

    total = len(records)
    if total == 0:
        print("No records to generate review CSV for.")
        return

    print(f"\n=== Generating Review CSV ===")
    print(f"Total segments: {total}")

    # Ensure output directory exists
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)

    # Columns requested:
    # id, video_id, start, end, dominant_speaker, transcript, language, emotion, quality_score, quality_issues, approved, rejection_reason
    fieldnames = [
        "id",
        "video_id",
        "start",
        "end",
        "dominant_speaker",
        "transcript",
        "language",
        "emotion",
        "quality_score",
        "quality_issues",
        "approved",
        "rejection_reason"
    ]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for idx, record in enumerate(records, start=1):
            quality_score = record.get("quality_score", 1.0)
            issues = record.get("quality_issues", [])
            issues_str = ", ".join(issues) if isinstance(issues, list) else str(issues)
            
            # Pre-populate approved field based on quality score (True for 1.0, False for 0.0)
            approved = "True" if quality_score >= 1.0 else "False"
            rejection_reason = issues_str if quality_score < 1.0 else ""
            
            writer.writerow({
                "id": record.get("segment_path", f"seg_{idx:05d}"),  # segment_path acts as a unique ID
                "video_id": record.get("video_id", ""),
                "start": record.get("start", 0.0),
                "end": record.get("end", 0.0),
                "dominant_speaker": record.get("dominant_speaker", "UNKNOWN"),
                "transcript": record.get("transcript", ""),
                "language": record.get("language", "unknown"),
                "emotion": record.get("emotion", "neutral"),
                "quality_score": quality_score,
                "quality_issues": issues_str,
                "approved": approved,
                "rejection_reason": rejection_reason
            })

    print(f"Generated review CSV: {output_csv}")
    print(f"Columns: {', '.join(fieldnames)}")
    print("\nInstructions:")
    print("1. Open the review.csv file to verify and edit the 'approved' and 'rejection_reason' columns.")
    print("2. Run 'python manual_review.py --filter' to produce the final dataset.")


def filter_by_acceptance(
    metadata_path="../data/segments_metadata_emotions.jsonl",
    review_csv="../data/review.csv",
    output_path="../data/segments_metadata_final.jsonl",
):
    """
    Filter segments based on the manual review CSV (approved == 'True' / 1).
    """
    # Load original records
    records = []
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    except FileNotFoundError:
        fallback_path = "../data/segments_metadata.jsonl"
        print(f"Input metadata file not found: {metadata_path}. Trying fallback: {fallback_path}")
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                for line in f:
                    records.append(json.loads(line))
        except FileNotFoundError:
            print("No source segments metadata file found.")
            return
            
    # Load review decisions
    approved_records = []
    rejected_records = []
    
    try:
        with open(review_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                video_id = row.get("video_id", "").strip()
                try:
                    start = float(row.get("start", 0.0))
                    end = float(row.get("end", 0.0))
                except ValueError:
                    continue
                
                approved_str = row.get("approved", "").strip().upper()
                rejection_reason = row.get("rejection_reason", "").strip()
                
                # Find matching record in memory
                match = None
                for r in records:
                    if r.get("video_id") == video_id:
                        if abs(r.get("start", 0.0) - start) < 0.01 and abs(r.get("end", 0.0) - end) < 0.01:
                            match = r
                            break
                            
                if not match:
                    # Try fallback to matching by ID (segment_path)
                    seg_id = row.get("id", "").strip()
                    for r in records:
                        if r.get("segment_path") == seg_id:
                            match = r
                            break
                
                if match:
                    # Update fields from the CSV review (e.g. transcript edits or emotion edits)
                    if "transcript" in row:
                        match["transcript"] = row["transcript"]
                    if "emotion" in row:
                        match["emotion"] = row["emotion"]
                    
                    # Check approved status
                    if approved_str in ["TRUE", "T", "YES", "Y", "1"]:
                        match["approved"] = True
                        match["rejection_reason"] = ""
                        approved_records.append(match)
                    else:
                        match["approved"] = False
                        match["rejection_reason"] = rejection_reason
                        rejected_records.append(match)
                else:
                    print(f"Warning: Record not found matching video_id={video_id}, start={start}, end={end}")
                    
    except FileNotFoundError:
        print(f"Review CSV not found at: {review_csv}")
        print("Please run with --generate first.")
        return

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Write approved final records
    with open(output_path, "w", encoding="utf-8") as f:
        for record in approved_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    # Write rejected records for tracing
    rejected_path = output_path.replace("_final.jsonl", "_rejected.jsonl")
    with open(rejected_path, "w", encoding="utf-8") as f:
        for record in rejected_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    total_decisions = len(approved_records) + len(rejected_records)
    print(f"\n=== Manual Review Filter Summary ===")
    print(f"Total reviewed decisions: {total_decisions}")
    print(f"Approved (Final Dataset): {len(approved_records)}")
    print(f"Rejected: {len(rejected_records)}")
    if total_decisions > 0:
        print(f"Acceptance rate: {100*len(approved_records)/total_decisions:.1f}%")
    print(f"\nSaved final approved dataset to: {output_path}")
    print(f"Saved rejected dataset to: {rejected_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Manual Review Workflow")
    parser.add_argument("--generate", action="store_true", help="Generate review.csv")
    parser.add_argument("--filter", action="store_true", help="Filter final JSONL based on review.csv")
    args = parser.parse_args()
    
    if args.filter:
        filter_by_acceptance()
    elif args.generate:
        generate_review_csv()
    else:
        # Default behavior is to generate if review.csv does not exist, otherwise show help
        if not os.path.exists("../data/review.csv"):
            generate_review_csv()
        else:
            parser.print_help()

# if __name__ == "__main__":
#     main()
