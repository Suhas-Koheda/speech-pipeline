#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path
from langdetect import detect, DetectorFactory

# Ensure reproducible langdetect results
DetectorFactory.seed = 0

ROOT_DIR = Path(__file__).resolve().parent.parent

def has_telugu_unicode(text):
    return any('\u0c00' <= c <= '\u0c7f' for c in text)

def should_relabel_to_english(transcript):
    if not transcript or not transcript.strip():
        return False

    # If there is Telugu script anywhere, leave it alone
    if has_telugu_unicode(transcript):
        return False

    try:
        lang = detect(transcript)
    except Exception:
        return False

    # Pure English only
    return lang == "en"

def backfill_and_relabel():
    metadata_path = ROOT_DIR / "data" / "metadata.json"
    metadata_by_id = {}
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            try:
                metadata_list = json.load(f)
                for item in metadata_list:
                    vid_id = item.get("video_id")
                    if vid_id:
                        metadata_by_id[vid_id] = item
            except Exception as e:
                print(f"Warning: could not parse metadata.json: {e}")

    # Process speech_review_all file
    review_path = ROOT_DIR / "data" / "speech_review_all_2026-06-18T14-04-55.json"
    if not review_path.exists():
        print(f"Error: {review_path} not found.")
        return

    with open(review_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    total_segments = len(records)
    relabelled_to_en = 0
    unchanged = 0

    for record in records:
        vid_id = record.get("video_id")
        meta = metadata_by_id.get(vid_id, {})

        # Apply source metadata backfill
        youtube_url = record.get("youtube_url") or record.get("url") or meta.get("youtube_url") or meta.get("url")
        if not youtube_url and vid_id:
            youtube_url = f"https://www.youtube.com/watch?v={vid_id}"
        record["youtube_url"] = youtube_url or ""
        
        channel_name = record.get("channel_name") or record.get("channel") or meta.get("channel_name") or meta.get("channel") or ""
        record["channel_name"] = channel_name
        
        video_title = record.get("video_title") or record.get("title") or meta.get("video_title") or meta.get("title") or ""
        record["video_title"] = video_title

        # Determine transcript text to analyze (final or original)
        transcript = record.get("corrected_transcript") or record.get("transcript") or record.get("original_transcript") or ""
        
        if should_relabel_to_english(transcript):
            record["language"] = "en-IN"
            relabelled_to_en += 1
        else:
            unchanged += 1

    # Save changes back
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    # Backfill other jsonl files in data directory to ensure absolute pipeline consistency
    data_dir = ROOT_DIR / "data"
    for file_path in data_dir.glob("*.jsonl"):
        updated_lines = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        vid_id = rec.get("video_id")
                        meta = metadata_by_id.get(vid_id, {})

                        # Apply source metadata backfill
                        youtube_url = rec.get("youtube_url") or rec.get("url") or meta.get("youtube_url") or meta.get("url")
                        if not youtube_url and vid_id:
                            youtube_url = f"https://www.youtube.com/watch?v={vid_id}"
                        rec["youtube_url"] = youtube_url or ""
                        
                        channel_name = rec.get("channel_name") or rec.get("channel") or meta.get("channel_name") or meta.get("channel") or ""
                        rec["channel_name"] = channel_name
                        
                        video_title = rec.get("video_title") or rec.get("title") or meta.get("video_title") or meta.get("title") or ""
                        rec["video_title"] = video_title

                        transcript = rec.get("corrected_transcript") or rec.get("transcript") or rec.get("original_transcript") or ""
                        if should_relabel_to_english(transcript):
                            rec["language"] = "en-IN"

                        updated_lines.append(json.dumps(rec, ensure_ascii=False))
                    except Exception as parse_err:
                        print(f"Skipping line in {file_path.name} due to error: {parse_err}")
                        updated_lines.append(line.strip())
        
        with open(file_path, "w", encoding="utf-8") as f:
            for line in updated_lines:
                f.write(line + "\n")
        # print(f"Backfilled: {file_path.name}")

    # Output stats in the exact required JSON format
    stats = {
        "total_segments": total_segments,
        "relabelled_to_en": relabelled_to_en,
        "unchanged": unchanged
    }
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    backfill_and_relabel()
