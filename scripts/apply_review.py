"""
Apply Manual Review Decisions

Reads the review decisions from review_results.csv and outputs:
- data/segments_metadata_final.jsonl (Approved segments)
- data/segments_metadata_rejected.jsonl (Rejected / Unreviewed segments)
"""

import json
import csv
import os
from pathlib import Path

def apply_review():
    print("=== Applying Manual Review Decisions ===")
    
    # Resolve project root based on script location
    ROOT_DIR = Path(__file__).resolve().parent.parent
    
    # 1. Discover review_results.csv
    csv_paths = [
        ROOT_DIR / "data" / "review_results.csv",
        ROOT_DIR / "review" / "review_results.csv",
        ROOT_DIR / "review_results.csv",
        Path("review_results.csv")
    ]
    
    selected_csv = None
    for p in csv_paths:
        if p.exists():
            selected_csv = p
            break
            
    if not selected_csv:
        print("Error: review_results.csv not found.")
        print("Please place the exported 'review_results.csv' in one of these locations:")
        for p in csv_paths:
            print(f"  - {p}")
        return
        
    print(f"Loading decisions from: {selected_csv}")
    
    # Decisions map: segment_path -> {approved: bool, rejection_reason: str, notes: str}
    decisions = {}
    try:
        with open(selected_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                path = row.get("segment_path", "").strip()
                approved_str = row.get("approved", "").strip().lower()
                approved = approved_str in ["true", "1", "yes"]
                
                decisions[path] = {
                    "approved": approved,
                    "rejection_reason": row.get("rejection_reason", "").strip(),
                    "notes": row.get("notes", "").strip()
                }
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
        
    print(f"Loaded {len(decisions)} decisions from CSV.")
    
    # 2. Discover segments metadata file (same file that was used to feed the app)
    metadata_paths = [
        ROOT_DIR / "data" / "segments_metadata_emotions.jsonl",
        ROOT_DIR / "data" / "segments_metadata_filtered.jsonl",
        ROOT_DIR / "data" / "segments_metadata.jsonl"
    ]
    
    selected_metadata = None
    records = []
    
    for p in metadata_paths:
        if p.exists():
            selected_metadata = p
            break
            
    if not selected_metadata:
        print("Error: Original segments metadata file not found in data/ directory.")
        return
        
    print(f"Loading original segments from: {selected_metadata}")
    with open(selected_metadata, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    # Determine outputs in the same directory as the metadata
    output_dir = selected_metadata.parent
    
    final_path = output_dir / "segments_metadata_final.jsonl"
    rejected_path = output_dir / "segments_metadata_rejected.jsonl"
    
    approved_records = []
    rejected_records = []
    unreviewed_count = 0
    
    for record in records:
        path = record.get("segment_path", "")
        
        # Match decision
        dec = decisions.get(path)
        
        if dec:
            record["approved"] = dec["approved"]
            record["notes"] = dec["notes"]
            
            if dec["approved"]:
                record["rejection_reason"] = ""
                approved_records.append(record)
            else:
                record["rejection_reason"] = dec["rejection_reason"] or "rejected_without_reason"
                rejected_records.append(record)
        else:
            # Unreviewed segment
            record["approved"] = False
            record["rejection_reason"] = "unreviewed"
            record["notes"] = ""
            rejected_records.append(record)
            unreviewed_count += 1
            
    # Write outputs
    with open(final_path, "w", encoding="utf-8") as f:
        for r in approved_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    with open(rejected_path, "w", encoding="utf-8") as f:
        for r in rejected_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    print(f"\n=== Review Application Summary ===")
    print(f"Total original segments: {len(records)}")
    print(f"Approved (Final Dataset): {len(approved_records)}")
    print(f"Rejected: {len(rejected_records) - unreviewed_count}")
    print(f"Unreviewed: {unreviewed_count}")
    print(f"\nSaved approved segments to: {final_path}")
    print(f"Saved rejected segments to: {rejected_path}")

if __name__ == "__main__":
    apply_review()
