import json
import torchaudio
from pathlib import Path
import tempfile
import numpy as np
import os
from dotenv import load_dotenv

from sarvamai import SarvamAI

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    raise ValueError("SARVAM_API_KEY not found in environment variables. Please set it in .env file or export it.")

client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

TARGET_SR = 16000


def transcribe(
    segment_path,
):
    """
    Transcribe audio segment using Sarvam API with auto language detection.
    
    Sarvam will automatically detect the language from the audio.
    
    Args:
        segment_path: Path to the audio segment file
    
    Returns:
        Tuple of (transcript, detected_language, confidence)
    """
    try:
        if not os.path.exists(segment_path):
            # Try relative path check if it doesn't exist directly (in case script is run from a different CWD)
            path_obj = Path(segment_path)
            if not path_obj.exists():
                print(f"Warning: Segment file not found: {segment_path}")
                return "", "unknown", 0.0
        
        response = client.speech_to_text.transcribe(
            audio_file_path=str(segment_path),
        )
        
        # Extract transcript, detected language, and confidence from response
        transcript = response.get("transcript", "") if isinstance(response, dict) else str(response)
        detected_language = response.get("language", "unknown") if isinstance(response, dict) else "unknown"
        confidence = response.get("confidence", 1.0) if isinstance(response, dict) else 1.0
        
        return transcript, detected_language, confidence
    
    except Exception as e:
        print(f"Transcription error for {segment_path}: {e}")
        return "", "unknown", 0.0


def update_segments_metadata(
    metadata_path="../data/segments_metadata.jsonl",
):
    """
    Add transcripts and language detection to segments.
    """
    records = []

    with open(
        metadata_path,
        "r",
        encoding="utf-8",
    ) as f:
        for line in f:
            records.append(
                json.loads(line)
            )

    total = len(records)
    successful = 0
    failed = 0

    for idx, record in enumerate(
        records,
        start=1,
    ):
        try:
            segment_path = record.get("segment_path", "")
            
            # Transcribe segment - Sarvam will auto-detect language
            transcript, detected_lang, confidence = transcribe(
                segment_path,
            )

            record["transcript"] = transcript
            record["language"] = detected_lang
            record["transcription_confidence"] = confidence

            successful += 1

            print(
                f"[{idx}/{total}] "
                f"{detected_lang.upper()} | "
                f"{transcript[:50]}"
            )

        except Exception as e:
            failed += 1
            print(
                f"Failed to transcribe record {idx}: {record.get('segment_path')}"
            )
            print(f"Error: {e}")

            record["transcript"] = ""
            record["language"] = "unknown"
            record["transcription_confidence"] = 0.0

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as f:
        for record in records:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"\n=== Transcription Summary ==="
    )
    print(
        f"Total records: {total}"
    )
    print(
        f"Successful: {successful}"
    )
    print(
        f"Failed: {failed}"
    )


def main():
    update_segments_metadata()

# if __name__ == "__main__":
#     main()