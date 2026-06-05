import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
ORIGINAL_METADATA = DATA_DIR / "segments_metadata.jsonl"
DATASET_DIR = BASE / "telangana-speech-dataset-v0"
AUDIO_DIR = DATASET_DIR / "audio"
NUM_SEGMENTS = None  # None = all valid segments


def read_metadata(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def has_valid_transcript(record):
    transcript = record.get("transcript", "").strip()
    return len(transcript) > 0


def transform_record(record, new_segment_name):
    segment_path = Path(record["segment_path"])

    return {
        "audio": f"audio/{new_segment_name}",
        "transcript": record["transcript"],
        "language": "te",
        "speaker": "unknown",
        "source": "youtube",
        "video_id": record["video_id"],
        "channel": record["channel"],
        "start": record["start"],
        "end": record["end"],
    }


def copy_segment(record, new_segment_name):
    src = (DATA_DIR / record["segment_path"]).resolve()
    dst = AUDIO_DIR / new_segment_name
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  Copied: {new_segment_name}")
    else:
        print(f"  WARNING: source not found: {src}")


def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    all_records = read_metadata(ORIGINAL_METADATA)
    print(f"Total records: {len(all_records)}")

    valid = [r for r in all_records if has_valid_transcript(r)]
    skipped = len(all_records) - len(valid)
    print(f"Valid (non-empty transcript): {len(valid)}")
    print(f"Skipped (empty transcript): {skipped}")

    selected = valid[:NUM_SEGMENTS]
    print(f"\nSelected {len(selected)} segments for v0")

    transformed = []
    for idx, record in enumerate(selected, start=1):
        new_name = f"segment_{idx:05d}.wav"
        copy_segment(record, new_name)
        transformed.append(transform_record(record, new_name))

    metadata_path = DATASET_DIR / "metadata.jsonl"
    with open(metadata_path, "w", encoding="utf-8") as f:
        for record in transformed:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nTransformed metadata written: {metadata_path}")
    print(f"Total audio files in dataset: {len(transformed)}")


if __name__ == "__main__":
    main()
