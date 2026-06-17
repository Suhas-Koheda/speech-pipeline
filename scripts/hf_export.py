"""
HuggingFace Dataset Export

Exports final TTS training dataset to HuggingFace dataset format.

Schema:
{
    \"audio\": {
        \"path\": str,
        \"array\": np.ndarray,
        \"sampling_rate\": int
    },
    \"text\": str,
    \"language\": str,
    \"emotion\": str,
    \"speaker\": str,
    \"duration\": float,
    \"video_id\": str,
    \"channel\": str,
}
"""

import json
from pathlib import Path
import numpy as np
import torchaudio
from datasets import Dataset, Audio, DatasetDict, load_dataset
import soundfile as sf


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
    Prepare a single record for HuggingFace dataset.
    
    Args:
        segment_record: Dictionary containing segment metadata
    
    Returns:
        Dictionary with HuggingFace dataset schema
    """
    return {
        "audio_path": segment_record.get("segment_path", ""),
        "text": segment_record.get("transcript", ""),
        "language": segment_record.get("language", "unknown"),
        "emotion": segment_record.get("emotion", "neutral"),
        "speaker": segment_record.get("dominant_speaker", "UNKNOWN"),
        "duration": segment_record.get("duration", 0.0),
        "video_id": segment_record.get("video_id", ""),
        "channel": segment_record.get("channel", ""),
        "quality_score": segment_record.get("quality_score", 1.0),
    }


def create_hf_dataset(
    input_path="../data/segments_metadata_final.jsonl",
    dataset_name="tts-training-dataset",
    push_to_hub=False,
    hub_repo_name="username/tts-training-dataset",
    hub_token=None,
):
    """
    Create HuggingFace dataset from segments metadata.
    
    Args:
        input_path: Path to final segments metadata
        dataset_name: Name for the dataset
        push_to_hub: Whether to push to HuggingFace Hub
        hub_repo_name: HuggingFace Hub repository name
        hub_token: HuggingFace API token for pushing
    
    Returns:
        Dataset object
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
            audio_path = Path(prepared["audio_path"])
            if not audio_path.exists():
                print(f"Warning: Audio file not found: {audio_path}")
                continue
            
            dataset_records.append(prepared)
            
            if idx % 100 == 0:
                print(f"Prepared {idx}/{total} records")
        
        except Exception as e:
            print(f"Error preparing record {idx}: {e}")
            continue
    
    print(f"Successfully prepared {len(dataset_records)} records")
    
    # Create dataset from dictionaries
    dataset = Dataset.from_dict({
        key: [r[key] for r in dataset_records]
        for key in dataset_records[0].keys()
    })
    
    # Cast audio column
    dataset = dataset.cast_column("audio_path", Audio(sampling_rate=SAMPLING_RATE))
    
    # Rename for proper schema
    dataset = dataset.rename_column("audio_path", "audio")
    
    print(f"\nDataset created with {len(dataset)} examples")
    print(f"Features: {dataset.features}")
    
    # Save locally
    output_dir = Path(f"../datasets/{dataset_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    dataset.save_to_disk(str(output_dir))
    print(f"\nSaved to: {output_dir}")
    
    # Optionally push to Hub
    if push_to_hub:
        if not hub_token:
            print("Warning: hub_token not provided, skipping Hub upload")
        else:
            try:
                print(f"\nPushing to Hub: {hub_repo_name}")
                dataset.push_to_hub(
                    hub_repo_name,
                    token=hub_token,
                    private=True,
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
    Split dataset into train/val/test.
    
    Args:
        dataset: HuggingFace Dataset
        train_size: Training set percentage
        val_size: Validation set percentage
        test_size: Test set percentage
    
    Returns:
        DatasetDict with splits
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
    output_format="parquet",  # or "arrow", "csv"
    split=True,
):
    """
    Export dataset in various formats.
    
    Args:
        input_path: Path to final segments metadata
        dataset_name: Name for the dataset
        output_format: Export format (parquet, arrow, csv)
        split: Whether to split into train/val/test
    """
    # Create dataset
    dataset = create_hf_dataset(input_path, dataset_name)
    
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
    
    for split_name, split_dataset in dataset_dict.items():
        output_path = output_dir / split_name
        
        if output_format == "parquet":
            split_dataset.to_parquet(str(output_path))
            print(f"Exported {split_name} to parquet")
        
        elif output_format == "csv":
            split_dataset.to_csv(str(output_path))
            print(f"Exported {split_name} to CSV")
        
        elif output_format == "arrow":
            split_dataset.save_to_disk(str(output_path))
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
    
    Args:
        dataset_name: Name of the dataset
        description: Dataset description
        languages: List of languages
        emotions: List of emotions
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
print(sample["text"])
print(f"Duration: {{sample['duration']}}s")
print(f"Emotion: {{sample['emotion']}}")
```

## Audio Format
- Sampling rate: 16 kHz
- Channels: Mono
- Format: WAV

## License
CC-BY-4.0

## Citation

@dataset{{{dataset_name},
  title={{{dataset_name}}},
  author={{Unknown Haas}},
  year={{2026}}
}}
"""
    
    output_path = Path(f"../datasets/{dataset_name}/README.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(card_content)
    
    print(f"Generated dataset card: {output_path}")


if __name__ == "__main__":
    # Create and export dataset
    export_dataset(
        dataset_name="tts-training-dataset",
        output_format="parquet",
        split=True
    )
    
    # Generate dataset card
    generate_dataset_card(
        dataset_name="tts-training-dataset",
        description="High-quality TTS training dataset with emotion tags",
    )
