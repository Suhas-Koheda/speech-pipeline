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
    """Load segments metadata from JSONL file."""
    records = []
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    except FileNotFoundError:
        print(f"File not found: {metadata_path}")
        return []
    
    return records


def prepare_dataset_record(segment_record):
    """
    Prepare a single record matching the HuggingFace dataset schema.
    Only fields backed by real data are included:
      - audio, transcript, language, speaker_id: from Sarvam ASR
      - style, emotion: from Sarvam LLM (tag_style.py)
    """
    record = {
        "audio": segment_record.get("segment_path", ""),
        "transcript": segment_record.get("transcript", ""),
        "language": segment_record.get("language", "unknown"),
        "speaker_id": segment_record.get("dominant_speaker", "UNKNOWN"),
        "style": segment_record.get("style", "neutral"),
        "emotion": segment_record.get("emotion", "neutral"),
    }

    return record


def create_hf_dataset(
    input_path="../data/segments_metadata_final.jsonl",
    dataset_name="tts-training-dataset",
    push_to_hub=False,
    hub_repo_name=None,
):
    """
    Create HuggingFace dataset from segments metadata.
    """
    print(f"\n=== Creating HuggingFace Dataset ===")
    
    # Load metadata
    records = load_segments_metadata(input_path)
    
    if not records:
        print("No records found!")
        return None
    
    total = len(records)
    print(f"Total segments: {total}")
    
    # Prepare records for dataset
    dataset_records = []
    
    for idx, record in enumerate(records, start=1):
        try:
            prepared = prepare_dataset_record(record)
            
            # Verify audio file exists
            audio_path = Path(prepared["audio"])
            if not audio_path.exists():
                # Check relative path
                if not Path(record.get("segment_path", "")).exists():
                    print(f"Warning: Audio file not found: {audio_path}")
                    continue
            
            dataset_records.append(prepared)
            
            if idx % 100 == 0:
                print(f"Prepared {idx}/{total} records")
        
        except Exception as e:
            print(f"Error preparing record {idx}: {e}")
            continue
    
    print(f"Successfully prepared {len(dataset_records)} records")
    
    if not dataset_records:
        print("No valid records to build dataset.")
        return None
        
    # Create dataset from dictionaries
    dataset = Dataset.from_dict({
        key: [r[key] for r in dataset_records]
        for key in dataset_records[0].keys()
    })
    
    # Cast audio column
    dataset = dataset.cast_column("audio", Audio(sampling_rate=SAMPLING_RATE))
    
    print(f"\nDataset created with {len(dataset)} examples")
    print(f"Features: {dataset.features}")
    
    # Save locally
    output_dir = Path(f"../datasets/{dataset_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    dataset.save_to_disk(str(output_dir))
    print(f"\nSaved to: {output_dir}")
    
    # Optionally push to Hub (Public as requested)
    if push_to_hub:
        hub_token = os.getenv("HF_TOKEN")
        if not hub_token:
            hub_token = None
        if not hub_repo_name:
            print("Warning: hub_repo_name not specified, skipping Hub upload")
        else:
            try:
                print(f"\nPushing to Hub: {hub_repo_name} (Public)")
                dataset.push_to_hub(
                    hub_repo_name,
                    token=hub_token,
                    private=False,  # PUBLIC dataset
                )
                print(f"Successfully pushed to {hub_repo_name}")
            except Exception as e:
                print(f"Error pushing to Hub: {e}")
    
    return dataset


def split_dataset(
    dataset,
    train_size=0.8,
    val_size=0.1,
    test_size=0.1,
):
    """
    Split dataset into train/val/test splits.
    """
    print(f"\n=== Splitting Dataset ===")
    
    # Normalize sizes
    total = train_size + val_size + test_size
    train_size /= total
    val_size /= total
    test_size /= total
    
    # First split: train vs rest
    train_val_split = dataset.train_test_split(
        test_size=(1 - train_size),
        seed=42
    )
    
    train = train_val_split["train"]
    rest = train_val_split["test"]
    
    # Second split: val vs test
    val_test_split = rest.train_test_split(
        test_size=test_size/(val_size + test_size),
        seed=42
    )
    
    val = val_test_split["train"]
    test = val_test_split["test"]
    
    dataset_dict = DatasetDict({
        "train": train,
        "validation": val,
        "test": test,
    })
    
    print(f"Train: {len(train)} examples")
    print(f"Validation: {len(val)} examples")
    print(f"Test: {len(test)} examples")
    
    return dataset_dict


def export_dataset(
    input_path="../data/segments_metadata_final.jsonl",
    dataset_name="tts-training-dataset",
    output_format="parquet",
    split=True,
    push_to_hub=False,
    hub_repo_name=None,
):
    """
    Export dataset in various formats.
    """
    # Create dataset
    dataset = create_hf_dataset(
        input_path=input_path,
        dataset_name=dataset_name,
        push_to_hub=push_to_hub,
        hub_repo_name=hub_repo_name
    )
    
    if dataset is None:
        return
    
    # Split if requested
    if split:
        dataset_dict = split_dataset(dataset)
    else:
        dataset_dict = DatasetDict({"full": dataset})
    
    # Export in specified format
    output_dir = Path(f"../datasets/{dataset_name}_exported")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n=== Exporting Dataset ===")
    
    for split_name, sub_dataset in dataset_dict.items():
        output_path = output_dir / split_name
        
        if output_format == "parquet":
            sub_dataset.to_parquet(str(output_path))
            print(f"Exported {split_name} to parquet")
        
        elif output_format == "csv":
            sub_dataset.to_csv(str(output_path))
            print(f"Exported {split_name} to CSV")
        
        elif output_format == "arrow":
            sub_dataset.save_to_disk(str(output_path))
            print(f"Exported {split_name} to Arrow")
    
    print(f"\nDataset exported to: {output_dir}")
    
    return dataset_dict


def generate_dataset_card(
    dataset_name="tts-training-dataset",
    description="High-quality TTS training dataset",
    languages=["te", "en"],
    emotions=None,
):
    """
    Generate a README.md card for the dataset.
    """
    if emotions is None:
        emotions = ["neutral", "conversational", "formal", "excited", "happy", 
                   "sad", "angry", "questioning", "serious"]
    
    card_content = f"""---
license: cc-by-4.0
language: {', '.join(languages)}
datasets:
- youtube
task_ids:
- speech-synthesis
---

# {dataset_name}

{description}

## Dataset Details

### Languages
{', '.join(languages)}

### Emotions/Styles
{', '.join(emotions)}

## Dataset Statistics

See `statistics.json` for detailed statistics including:
- Total duration
- Language distribution
- Emotion distribution
- Quality metrics

## Usage

```python
from datasets import load_dataset

dataset = load_dataset(
    "path/to/{dataset_name}",
    split="train"
)

# Access a sample
sample = dataset[0]
print(sample["transcript"])
print(f"Speaker ID: {{sample['speaker_id']}}")
print(f"Emotion: {{sample['emotion']}}")
```

## Audio Format
- Sampling rate: 16 kHz
- Channels: Mono
- Format: WAV

## License
CC-BY-4.0
"""
    
    output_path = Path(f"../datasets/{dataset_name}/README.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(card_content)
    
    print(f"Generated dataset card: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="HuggingFace Dataset Export")
    parser.add_argument("--repo", type=str, help="HuggingFace repository name (e.g. username/repo)")
    parser.add_argument("--push", action="store_true", help="Push dataset to HuggingFace Hub")
    args, unknown = parser.parse_known_args()
    
    # Create and export dataset
    export_dataset(
        dataset_name="tts-training-dataset",
        output_format="parquet",
        split=True,
        push_to_hub=args.push,
        hub_repo_name=args.repo
    )
    
    # Generate dataset card
    generate_dataset_card(
        dataset_name="tts-training-dataset",
        description="High-quality TTS training dataset with emotion and style tags",
    )

# if __name__ == "__main__":
#     main()