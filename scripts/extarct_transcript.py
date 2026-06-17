import json
import torchaudio
from pathlib import Path
import tempfile
import numpy as np

from sarvamai import SarvamAI

client = SarvamAI(
    api_subscription_key="sk_47ddcxjr_zAcEh9HqfHea2eXrKolShDK4"
)

TARGET_SR = 16000


def transcribe(
    audio_path,
    start_time,
    end_time,
):
    """
    Transcribe audio segment using Sarvam API with auto language detection.
    
    Sarvam will automatically detect the language from the audio.
    
    Args:
        audio_path: Path to full audio file
        start_time: Start time in seconds
        end_time: End time in seconds
    
    Returns:
        Tuple of (transcript, detected_language, confidence)
    """
    try:
        # Load audio and extract segment
        wav, sr = torchaudio.load(audio_path)
        
        # Convert to mono if stereo
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        
        # Calculate sample indices
        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)
        
        # Extract segment
        segment_wav = wav[:, start_sample:end_sample]
        
        # Resample to target rate if needed
        if sr != TARGET_SR:
            resampler = torchaudio.transforms.Resample(sr, TARGET_SR)
            segment_wav = resampler(segment_wav)
        
        # Save segment to temporary file for API call
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            torchaudio.save(tmp_path, segment_wav, TARGET_SR)
        
        try:
            # Let Sarvam auto-detect language - no language_code parameter
            response = client.speech_to_text.transcribe(
                audio_file_path=tmp_path,
            )
            
            # Extract transcript, detected language, and confidence from response
            transcript = response.get("transcript", "") if isinstance(response, dict) else str(response)
            detected_language = response.get("language", "unknown") if isinstance(response, dict) else "unknown"
            confidence = response.get("confidence", 1.0) if isinstance(response, dict) else 1.0
            
            return transcript, detected_language, confidence
        
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    except Exception as e:
        print(f"Transcription error: {e}")
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
            # Transcribe segment - Sarvam will auto-detect language
            transcript, detected_lang, confidence = transcribe(
                record["audio_path"],
                record["start"],
                record["end"],
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
                f"Failed: {record['video_id']} "
                f"{record['start']}-{record['end']}"
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


if __name__ == "__main__":
    update_segments_metadata()