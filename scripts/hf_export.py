"""
HuggingFace Dataset Export

Exports final TTS training dataset to HuggingFace dataset format.

Schema:
* audio: {"path": "...", "bytes": ...}
* transcript: str
* language: str
* speaker_id: str
* emotion: str
"""

import json
import os
from pathlib import Path
import numpy as np
from datasets import Dataset, Audio, DatasetDict
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

SAMPLING_RATE = 16000


def load_segments_metadata(metadata_path):
    """Load segments metadata from JSON or JSONL file."""
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            if content.startswith("["):
                return json.loads(content)
            else:
                return [json.loads(line) for line in content.split("\n") if line.strip()]
    except Exception as e:
        print(f"Error loading {metadata_path}: {e}")
        return []


def prepare_accepted_record(r):
    audio_path = r.get("segment_path", "")
    p = Path(audio_path)
    if not p.exists():
        p_rel = ROOT_DIR / audio_path.replace("../", "")
        if p_rel.exists():
            p = p_rel
            
    p_abs = p.resolve()
    if p_abs.exists():
        audio_path = str(p_abs)
    else:
        print(f"Warning: Audio file not found: {audio_path}")
        
    return {
        "audio": audio_path,
        "transcript": r.get("corrected_transcript") or r.get("transcript") or r.get("original_transcript") or "",
        "language": r.get("language", "unknown"),
        "speaker_id": r.get("dominant_speaker") or r.get("speaker_id") or "UNKNOWN",
        "style": r.get("style"),
        "emotion": r.get("emotion"),
        "video_id": r.get("video_id", ""),
        "youtube_url": r.get("youtube_url", ""),
        "channel_name": r.get("channel_name", ""),
        "video_title": r.get("video_title", ""),
        "rejection_reason": "",
        "notes": "",
    }


def prepare_rejected_record(r):
    audio_path = r.get("segment_path", "")
    p = Path(audio_path)
    if not p.exists():
        p_rel = ROOT_DIR / audio_path.replace("../", "")
        if p_rel.exists():
            p = p_rel
            
    p_abs = p.resolve()
    if p_abs.exists():
        audio_path = str(p_abs)
    else:
        print(f"Warning: Audio file not found: {audio_path}")
        
    return {
        "audio": audio_path,
        "transcript": r.get("corrected_transcript") or r.get("transcript") or r.get("original_transcript") or "",
        "language": r.get("language", "unknown"),
        "speaker_id": r.get("dominant_speaker") or r.get("speaker_id") or "UNKNOWN",
        "style": r.get("style"),
        "emotion": r.get("emotion"),
        "video_id": r.get("video_id", ""),
        "youtube_url": r.get("youtube_url", ""),
        "channel_name": r.get("channel_name", ""),
        "video_title": r.get("video_title", ""),
        "rejection_reason": r.get("rejection_reason") or "",
        "notes": r.get("notes") or "",
    }


def compute_split_stats(records):
    total_segments = len(records)
    total_duration = sum(float(r.get("duration", 0)) for r in records)
    
    languages = {}
    styles = {}
    emotions = {}
    speakers = set()
    
    for r in records:
        dur = float(r.get("duration", 0))
        
        lang = r.get("language", "unknown")
        if lang not in languages:
            languages[lang] = {"count": 0, "duration": 0.0}
        languages[lang]["count"] += 1
        languages[lang]["duration"] += dur
        
        style = r.get("style") or "none"
        if style not in styles:
            styles[style] = {"count": 0, "duration": 0.0}
        styles[style]["count"] += 1
        styles[style]["duration"] += dur
        
        emotion = r.get("emotion") or "none"
        if emotion not in emotions:
            emotions[emotion] = {"count": 0, "duration": 0.0}
        emotions[emotion]["count"] += 1
        emotions[emotion]["duration"] += dur
        
        spk = r.get("dominant_speaker") or r.get("speaker_id") or "UNKNOWN"
        speakers.add(spk)
        
    return {
        "total_segments": total_segments,
        "total_duration_minutes": total_duration / 60.0,
        "languages": languages,
        "styles": styles,
        "emotions": emotions,
        "unique_speakers": len(speakers),
    }


def format_stats_markdown(split_name, stats):
    if not stats:
        return ""
        
    lang_lines = []
    for lang, data in sorted(stats["languages"].items()):
        lang_lines.append(f"  - **{lang}**: {data['count']} segments ({data['duration']/60.0:.2f} minutes)")
    lang_str = "\n".join(lang_lines)
    
    style_lines = []
    for style, data in sorted(stats["styles"].items(), key=lambda x: x[1]["count"], reverse=True):
        style_lines.append(f"  - **{style}**: {data['count']} segments ({data['duration']/60.0:.2f} minutes)")
    style_str = "\n".join(style_lines)
    
    emotion_lines = []
    for emotion, data in sorted(stats["emotions"].items(), key=lambda x: x[1]["count"], reverse=True):
        emotion_lines.append(f"  - **{emotion}**: {data['count']} segments ({data['duration']/60.0:.2f} minutes)")
    emotion_str = "\n".join(emotion_lines)
    
    markdown = f"""### `{split_name}` Split
- **Total Segments:** {stats['total_segments']}
- **Total Duration:** {stats['total_duration_minutes']:.2f} minutes
- **Unique Speakers:** {stats['unique_speakers']}

#### Distribution Breakdowns:
* **Language Distribution:**
{lang_str}
* **Style Distribution:**
{style_str}
* **Emotion Distribution:**
{emotion_str}
"""
    return markdown


def create_hf_dataset(
    input_path="../data/speech_review_all_2026-06-18T14-04-55.json",
    dataset_name="tts-training-dataset",
    push_to_hub=False,
    hub_repo_name=None,
):
    """
    Create HuggingFace dataset from segments metadata.
    """
    print(f"\n=== Loading human reviewed metadata from {input_path} ===")
    records = load_segments_metadata(input_path)
    
    if not records:
        print("No records found!")
        return None
        
    print(f"Total loaded records: {len(records)}")
    
    # 1. Separate accepted and rejected
    accepted_records = [r for r in records if r.get("review_status") == "accepted"]
    rejected_records = [r for r in records if r.get("review_status") == "rejected"]
    
    print(f"Accepted records count: {len(accepted_records)}")
    print(f"Rejected records count: {len(rejected_records)}")
    
    # 2. Construct balanced_60min split
    telugu = [r for r in accepted_records if r.get("language") == "te-IN"]
    english = [r for r in accepted_records if r.get("language") == "en-IN"]
    
    # Sort by duration descending
    telugu.sort(key=lambda x: float(x.get("duration", 0)), reverse=True)
    english.sort(key=lambda x: float(x.get("duration", 0)), reverse=True)
    
    # Accumulate up to TARGET = 1800 seconds (30 minutes)
    TARGET = 1800
    selected_te = []
    dur_te = 0.0
    for r in telugu:
        if dur_te >= TARGET:
            break
        selected_te.append(r)
        dur_te += float(r.get("duration", 0))
        
    selected_en = []
    dur_en = 0.0
    for r in english:
        if dur_en >= TARGET:
            break
        selected_en.append(r)
        dur_en += float(r.get("duration", 0))
        
    # Merge the two language lists in order (Telugu first, then English, each descending by duration)
    balanced_60min_records = selected_te + selected_en
    
    # Sort all splits consistently: Telugu first, then English, sorted by duration descending
    accepted_records.sort(key=lambda x: (0 if x.get("language") == "te-IN" else 1, -float(x.get("duration", 0))))
    rejected_records.sort(key=lambda x: (0 if x.get("language") == "te-IN" else 1, -float(x.get("duration", 0))))
    
    # Generate statistics
    stats = {
        "telugu_duration_seconds": dur_te,
        "english_duration_seconds": dur_en,
        "total_duration_seconds": dur_te + dur_en,
        "telugu_segments": len(selected_te),
        "english_segments": len(selected_en)
    }
    
    # Save statistics JSON
    stats_dir = Path("../data")
    stats_dir.mkdir(parents=True, exist_ok=True)
    stats_path = stats_dir / "balanced_60min_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
    print(f"Saved balanced_60min statistics to {stats_path}")
    
    # Before export verify that the required keys are present
    print("Verifying source metadata before export...")
    for rec in list(balanced_60min_records) + list(accepted_records) + list(rejected_records):
        for key in ["youtube_url", "channel_name", "video_title", "video_id"]:
            if key not in rec:
                print(f"Error: missing required source metadata key '{key}' in record: {rec}")
                assert key in rec, f"Missing required source metadata key: '{key}'"

    # 3. Prepare records for Dataset dict
    balanced_prepared = [prepare_accepted_record(r) for r in balanced_60min_records]
    full_accepted_prepared = [prepare_accepted_record(r) for r in accepted_records]
    rejected_prepared = [prepare_rejected_record(r) for r in rejected_records]
    
    # Create datasets from lists
    ds_balanced = Dataset.from_dict({
        key: [r[key] for r in balanced_prepared]
        for key in balanced_prepared[0].keys()
    })
    ds_balanced = ds_balanced.cast_column("audio", Audio(sampling_rate=SAMPLING_RATE))
    
    ds_full_accepted = Dataset.from_dict({
        key: [r[key] for r in full_accepted_prepared]
        for key in full_accepted_prepared[0].keys()
    })
    ds_full_accepted = ds_full_accepted.cast_column("audio", Audio(sampling_rate=SAMPLING_RATE))
    
    ds_rejected = Dataset.from_dict({
        key: [r[key] for r in rejected_prepared]
        for key in rejected_prepared[0].keys()
    })
    ds_rejected = ds_rejected.cast_column("audio", Audio(sampling_rate=SAMPLING_RATE))
    
    dataset_dict = DatasetDict({
        "balanced_60min": ds_balanced,
        "full_accepted": ds_full_accepted,
        "rejected": ds_rejected
    })
    
    print("\nDataset splits created:")
    for split_name, ds in dataset_dict.items():
        print(f"  - {split_name}: {len(ds)} examples")
        
    # Save locally
    output_dir = Path(f"../datasets/{dataset_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_dict.save_to_disk(str(output_dir))
    print(f"\nSaved DatasetDict to: {output_dir}")
    
    # Compute split stats and generate card
    split_stats = {
        "balanced_60min": compute_split_stats(balanced_60min_records),
        "full_accepted": compute_split_stats(accepted_records),
        "rejected": compute_split_stats(rejected_records),
    }
    
    # Compute review stats dynamically
    total_reviewed = len(records)
    accepted = len(accepted_records)
    rejected = len(rejected_records)
    acceptance_rate = (accepted / total_reviewed) * 100 if total_reviewed > 0 else 0.0
    
    corrected_count = sum(
        1 for r in accepted_records 
        if r.get("corrected_transcript") and r.get("corrected_transcript").strip() != (r.get("transcript") or r.get("original_transcript") or "").strip()
    )
    correction_rate = (corrected_count / accepted) * 100 if accepted > 0 else 0.0
    accepted_duration = sum(float(r.get("duration", 0)) for r in accepted_records)
    
    review_stats = {
        "total_reviewed": total_reviewed,
        "accepted": accepted,
        "rejected": rejected,
        "acceptance_rate": acceptance_rate,
        "correction_rate": correction_rate,
        "accepted_duration_minutes": accepted_duration / 60.0,
    }
    
    # Calculate unique sources (video/channel details)
    sources = {}
    for r in records:
        vid_id = r.get("video_id")
        if not vid_id:
            continue
        if vid_id not in sources:
            sources[vid_id] = {
                "channel": r.get("channel", "Unknown Channel"),
                "title": r.get("title", "Unknown Title"),
                "total_segments": 0,
                "accepted_segments": 0,
                "total_duration": 0.0,
                "accepted_duration": 0.0,
            }
        dur = float(r.get("duration", 0))
        sources[vid_id]["total_segments"] += 1
        sources[vid_id]["total_duration"] += dur
        if r.get("review_status") == "accepted":
            sources[vid_id]["accepted_segments"] += 1
            sources[vid_id]["accepted_duration"] += dur

    source_lines = [
        "| Channel | Video Title | Video Link | Total Segments | Accepted Segments | Total Duration | Accepted Duration |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    for vid_id, info in sorted(sources.items(), key=lambda x: x[1]["accepted_segments"], reverse=True):
        link = f"[Watch](https://www.youtube.com/watch?v={vid_id})"
        safe_title = info["title"].replace("|", "\\|")
        title_trunc = safe_title[:50] + "..." if len(safe_title) > 53 else safe_title
        source_lines.append(
            f"| {info['channel']} | {title_trunc} | {link} | {info['total_segments']} | {info['accepted_segments']} | {info['total_duration']/60.0:.2f} mins | {info['accepted_duration']/60.0:.2f} mins |"
        )
    source_table = "\n".join(source_lines)
    
    generate_dataset_card(
        dataset_name=dataset_name,
        split_stats=split_stats,
        review_stats=review_stats,
        source_table=source_table
    )
    
    # Optionally push to Hub (Public)
    if push_to_hub:
        hub_token = os.getenv("HF_TOKEN")
        if not hub_token:
            hub_token = None
        if not hub_repo_name:
            print("Warning: hub_repo_name not specified, skipping Hub upload")
        else:
            try:
                # Delete existing repo to prevent schema mismatch errors
                from huggingface_hub import HfApi
                api = HfApi()
                try:
                    print(f"Deleting existing repository '{hub_repo_name}' to clean up old schema/splits...")
                    api.delete_repo(repo_id=hub_repo_name, repo_type="dataset", token=hub_token)
                    print("Repository deleted successfully.")
                except Exception as delete_error:
                    print(f"Note: Repository delete skipped/failed (likely did not exist): {delete_error}")
 
                print(f"\nPushing DatasetDict to Hub: {hub_repo_name} (Public)")
                dataset_dict.push_to_hub(
                    hub_repo_name,
                    token=hub_token,
                    private=False,
                )
                print(f"Successfully pushed DatasetDict to Hub: {hub_repo_name}")
                
                # Push the README.md as the dataset card
                readme_path = output_dir / "README.md"
                if readme_path.exists():
                    from huggingface_hub import HfApi
                    print("Uploading README.md dataset card to Hub...")
                    api = HfApi()
                    api.upload_file(
                        path_or_fileobj=str(readme_path),
                        path_in_repo="README.md",
                        repo_id=hub_repo_name,
                        repo_type="dataset",
                        token=hub_token
                    )
                    print("Successfully uploaded README.md dataset card.")
            except Exception as e:
                print(f"Error pushing to Hub: {e}")
                
    return dataset_dict


def generate_dataset_card(
    dataset_name="tts-training-dataset",
    split_stats=None,
    review_stats=None,
    source_table="",
):
    """
    Generate a clean README.md card for the dataset.
    """
    stats_md = ""
    if split_stats:
        for split_name, stats in split_stats.items():
            stats_md += format_stats_markdown(split_name, stats) + "\n"
            
    review_stats_md = ""
    if review_stats:
        review_stats_md = f"""- **Total Reviewed:** {review_stats['total_reviewed']}
- **Accepted:** {review_stats['accepted']}
- **Rejected:** {review_stats['rejected']}
- **Acceptance Rate:** {review_stats['acceptance_rate']:.1f}%
- **Transcript Correction Rate:** {review_stats['correction_rate']:.1f}%
- **Accepted Duration:** {review_stats['accepted_duration_minutes']:.2f} minutes"""

    card_content = f"""---
license: cc-by-4.0
language:
- te
- en
pretty_name: Human Reviewed Telugu-English TTS Dataset
task_categories:
- text-to-speech
- automatic-speech-recognition
---

# Human Reviewed Telugu-English TTS Dataset

A manually reviewed multilingual TTS dataset created from publicly available educational and speech content.

## Dataset Splits & Distribution Metrics

{stats_md}
## Pipeline

YouTube Sources
→ Sarvam Speech-to-Text
→ Sarvam Speaker Diarization
→ Segment Extraction
→ Quality Filtering
→ Style & Emotion Tagging
→ Human Review
→ HuggingFace Export

## Human Review Statistics

{review_stats_md}

### Common Corrections:
- ASR spelling mistakes
- Code-mixed English/Telugu transcription errors
- Named entity corrections
- Diarization boundary issues
- Transcript/audio alignment issues

## Audio Source Details

The audio files for this dataset were sourced from various YouTube channels, segmented, and human-reviewed. Below is the detailed breakdown for each source video:

{source_table}

## Final Dataset Schema (for `balanced_60min` & `full_accepted`)

- `audio` (Audio column, 16kHz mono WAV)
- `transcript` (string, corrected speech transcript)
- `language` (string, "te-IN" or "en-IN")
- `speaker_id` (string, unique speaker label)
- `style` (string, conversational, educational, etc.)
- `emotion` (string, neutral, happy, excited, etc.)
- `video_id` (string, unique video identifier)
- `youtube_url` (string, link to original source video)
- `channel_name` (string, name of source YouTube channel)
- `video_title` (string, title of original source video)

## Rejected Dataset Schema

- `audio` (Audio column, 16kHz mono WAV)
- `transcript` (string, corrected speech transcript)
- `language` (string, "te-IN" or "en-IN")
- `speaker_id` (string, unique speaker label)
- `style` (string, conversational, educational, etc.)
- `emotion` (string, neutral, happy, excited, etc.)
- `video_id` (string, unique video identifier)
- `youtube_url` (string, link to original source video)
- `channel_name` (string, name of source YouTube channel)
- `video_title` (string, title of original source video)
- `rejection_reason` (string, reason segment was rejected)
- `notes` (string, additional human annotator notes)

## Source Metadata

Each sample preserves provenance information:

* YouTube URL
* Video ID
* Channel Name
* Original Video Title

This allows every segment to be traced back to its original source recording.

## License
CC-BY-4.0
"""
    output_path = Path(f"../datasets/{dataset_name}/README.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(card_content)
    print(f"Generated dataset card: {output_path}")


def export_dataset(
    input_path="../data/speech_review_all_2026-06-18T14-04-55.json",
    dataset_name="tts-training-dataset",
    output_format="parquet",
    push_to_hub=False,
    hub_repo_name=None,
):
    """
    Export dataset splits in various formats.
    """
    # Create dataset splits (this will also generate and save README.md card)
    dataset_dict = create_hf_dataset(
        input_path=input_path,
        dataset_name=dataset_name,
        push_to_hub=push_to_hub,
        hub_repo_name=hub_repo_name
    )
    
    if dataset_dict is None:
        return None
        
    # Export in specified format
    output_dir = Path(f"../datasets/{dataset_name}_exported")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n=== Exporting Dataset splits to Parquet ===")
    
    for split_name, sub_dataset in dataset_dict.items():
        output_path = output_dir / f"{split_name}.parquet"
        sub_dataset.to_parquet(str(output_path))
        print(f"Exported {split_name} to {output_path}")
        
    print(f"\nDataset splits successfully exported to: {output_dir}")
    return dataset_dict


def main():
    import argparse
    parser = argparse.ArgumentParser(description="HuggingFace Dataset Export")
    parser.add_argument("--repo", type=str, help="HuggingFace repository name (e.g. username/repo)")
    parser.add_argument("--push", action="store_true", help="Push dataset to HuggingFace Hub")
    args, unknown = parser.parse_known_args()
    
    export_dataset(
        dataset_name="tts-training-dataset",
        output_format="parquet",
        push_to_hub=args.push,
        hub_repo_name=args.repo
    )


if __name__ == "__main__":
    main()