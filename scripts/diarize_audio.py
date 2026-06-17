"""
ASR and Speaker Diarization Segment Generation Pipeline.

Uses Sarvam Cloud Diarization & Transcription results natively to define segment boundaries.
Splits long segments (>15s) intelligently and slices corresponding audio segments.
"""

import sys
import os
import json
import re
import tempfile
import glob
import time
import soundfile as sf
from pathlib import Path
from dotenv import load_dotenv

# Ensure the scripts/ directory is in python search path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from sarvamai import SarvamAI

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

# Test mode flag: if True, processes only the first video in the list.
TEST_MODE = False

def retry_api_call(func, *args, retries=3, initial_delay=2.0, backoff_factor=2.0, **kwargs):
    """
    Retries an API call in case of network/server failures with exponential backoff.
    """
    delay = initial_delay
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            func_name = func.__name__ if hasattr(func, "__name__") else str(func)
            print(f"[Attempt {attempt}/{retries}] API call to '{func_name}' failed: {e}")
            if attempt == retries:
                raise e
            print(f"Waiting {delay:.1f}s before retrying...")
            time.sleep(delay)
            delay *= backoff_factor
    if last_exc:
        raise last_exc

def save_stats(processed, failed, speakers, turns):
    stats = {
        "videos_processed": processed,
        "videos_failed": failed,
        "total_speakers": speakers,
        "total_turns": turns
    }
    stats_path = ROOT_DIR / "data" / "diarization_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
    print(f"\nDiarization stats saved to {stats_path}")

def save_transcript_response(video_id, response_data):
    transcripts_path = ROOT_DIR / "data" / "sarvam_transcripts.json"
    transcripts_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {}
    if transcripts_path.exists():
        try:
            with open(transcripts_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load existing sarvam_transcripts.json: {e}")
            
    data[video_id] = response_data
    
    with open(transcripts_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Saved raw Sarvam response for video {video_id} to {transcripts_path}")

def split_entry_recursively(entry):
    """
    Recursively splits entries longer than 15.0 seconds at sentence or word boundaries,
    estimating timestamps proportionally by character length.
    """
    start = float(entry.get("start_time_seconds", 0.0))
    end = float(entry.get("end_time_seconds", 0.0))
    transcript = entry.get("transcript", "").strip()
    sp_id = entry.get("speaker_id")
    
    dur = end - start
    if dur <= 15.0 or not transcript:
        return [entry]
        
    # Split by Telugu/English punctuation boundaries (. ? ! | || \n)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?|])\s+', transcript) if s.strip()]
    
    if len(sentences) > 1:
        total_chars = sum(len(s) for s in sentences)
        res = []
        curr_start = start
        for s in sentences:
            fraction = len(s) / total_chars
            s_dur = dur * fraction
            res.extend(split_entry_recursively({
                "transcript": s,
                "start_time_seconds": curr_start,
                "end_time_seconds": curr_start + s_dur,
                "speaker_id": sp_id
            }))
            curr_start += s_dur
        return res
        
    # Fallback to word splitting if a single sentence is > 15s
    words = transcript.split()
    if len(words) > 1:
        mid = len(words) // 2
        half1 = " ".join(words[:mid])
        half2 = " ".join(words[mid:])
        total_chars = len(half1) + len(half2)
        
        res = []
        dur1 = dur * (len(half1) / total_chars)
        res.extend(split_entry_recursively({
            "transcript": half1,
            "start_time_seconds": start,
            "end_time_seconds": start + dur1,
            "speaker_id": sp_id
        }))
        res.extend(split_entry_recursively({
            "transcript": half2,
            "start_time_seconds": start + dur1,
            "end_time_seconds": end,
            "speaker_id": sp_id
        }))
        return res
        
    return [entry]

def sanitize_name(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)

def diarize_audio(metadata):
    videos_processed = 0
    videos_failed = 0
    all_unique_speakers = set()
    total_turns = 0
    
    load_dotenv()
    api_key = os.getenv("SARVAM_API_KEY")
    
    client = None
    if api_key:
        client = SarvamAI(api_subscription_key=api_key)
        
    transcripts_path = ROOT_DIR / "data" / "sarvam_transcripts.json"
    cached_transcripts = {}
    if transcripts_path.exists():
        try:
            with open(transcripts_path, "r", encoding="utf-8") as f:
                cached_transcripts = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cached transcripts: {e}")
            
    all_candidate_records = []
    
    for video in metadata:
        title = video.get("title", "Unknown Video")
        audio_path = video.get("audio_path")
        video_id = video.get("video_id")
        
        if not video_id:
            print(f"Error: video_id is missing for video: {title}")
            videos_failed += 1
            continue
            
        # Resolve audio path
        if audio_path:
            abs_audio_path = ROOT_DIR / audio_path.replace("../", "")
        else:
            abs_audio_path = None
            
        if not abs_audio_path or not abs_audio_path.exists():
            print(f"Error: Audio file not found for video '{title}': {audio_path}")
            videos_failed += 1
            continue
            
        result = None
        # Check if already processed in cache
        if video_id in cached_transcripts:
            print(f"Loading cached Sarvam response for video: {title}")
            result = cached_transcripts[video_id]
        else:
            if not client:
                print(f"Error: SARVAM_API_KEY is missing. Cannot call API for: {title}")
                videos_failed += 1
                continue
                
            # Perform API call
            file_size_bytes = abs_audio_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            print(f"\n--- Investigating Audio File for Upload ---")
            print(f"Video Title: {title}")
            print(f"Audio Path: {abs_audio_path}")
            print(f"File Size: {file_size_mb:.2f} MB")
            print(f"----------------------------------------")
            
            try:
                with tempfile.TemporaryDirectory() as upload_tmp_dir:
                    temp_audio_path = Path(upload_tmp_dir) / f"{video_id}.wav"
                    try:
                        os.symlink(abs_audio_path.resolve(), temp_audio_path)
                    except Exception:
                        import shutil
                        shutil.copy(abs_audio_path, temp_audio_path)
                        
                    print("Creating batch speech-to-text job with diarization...")
                    job = retry_api_call(
                        client.speech_to_text_job.create_job,
                        model="saaras:v3",
                        mode="transcribe",
                        language_code="unknown",
                        with_diarization=True
                    )
                    
                    print(f"Uploading file: {temp_audio_path.name}")
                    upload_success = retry_api_call(job.upload_files, file_paths=[str(temp_audio_path)])
                    
                    if not upload_success:
                        raise ValueError("No files were uploaded to Sarvam. Aborting job.")
                        
                    print("Starting batch job...")
                    retry_api_call(job.start)
                    
                    print("Waiting for job to complete (polling)...")
                    retry_api_call(job.wait_until_complete)
                    
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        print("Downloading outputs...")
                        retry_api_call(job.download_outputs, output_dir=tmp_dir)
                        json_files = glob.glob(os.path.join(tmp_dir, "*.json"))
                        if not json_files:
                            raise ValueError("Failed to download or find results JSON.")
                            
                        with open(json_files[0], "r", encoding="utf-8") as f:
                            result = json.load(f)
                            
                        save_transcript_response(video_id, result)
            except Exception as e:
                print(f"Error querying Sarvam for video '{title}': {e}")
                videos_failed += 1
                continue
                
        if not result:
            print(f"Failed to get ASR result for video '{title}'.")
            videos_failed += 1
            continue
            
        # Extract and slice entries
        entries = []
        if "diarized_transcript" in result:
            entries = result["diarized_transcript"].get("entries", [])
        elif "entries" in result:
            entries = result["entries"]
            
        if not entries:
            print(f"Warning: No transcription entries found for video '{title}'.")
            videos_processed += 1
            continue
            
        print(f"Processing {len(entries)} raw transcription entries...")
        
        # Load the physical audio file for slicing
        audio_data, sr = sf.read(abs_audio_path)
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
            
        channel_name = sanitize_name(video.get("channel", "unknown_channel"))
        output_dir = ROOT_DIR / "segments" / channel_name / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Format speaker metadata for metadata.json compatibility
        speaker_metadata = {}
        
        sliced_count = 0
        for entry in entries:
            # Check speaker
            sp_id = entry.get("speaker_id")
            if sp_id is not None:
                try:
                    sp_name = f"SPEAKER_{int(sp_id):02d}"
                except ValueError:
                    sp_name = f"SPEAKER_{sp_id}"
                speaker = f"speaker_{sp_id}"
            else:
                sp_name = "UNKNOWN"
                speaker = "unknown"
                
            # Split recursively if duration > 15 seconds
            split_pieces = split_entry_recursively(entry)
            
            for piece in split_pieces:
                start = float(piece.get("start_time_seconds", 0.0))
                end = float(piece.get("end_time_seconds", 0.0))
                dur = end - start
                transcript_text = piece.get("transcript", "").strip()
                
                # Check for physical audio bounds
                start_sample = int(start * sr)
                end_sample = int(end * sr)
                
                if start_sample < 0:
                    start_sample = 0
                if end_sample > len(audio_data):
                    end_sample = len(audio_data)
                    
                if end_sample <= start_sample:
                    continue
                    
                # Slice physical wav file
                segment_audio = audio_data[start_sample:end_sample]
                segment_filename = f"segment_{sliced_count:05d}.wav"
                segment_path = output_dir / segment_filename
                
                sf.write(segment_path, segment_audio, sr)
                
                # Prepare record with both final and backwards-compatible schemas
                rel_segment_path = f"../segments/{channel_name}/{video_id}/{segment_filename}"
                record = {
                    "video_id": video_id,
                    "channel": video.get("channel"),
                    "title": title,
                    "audio_path": rel_segment_path,       # final schema
                    "segment_path": rel_segment_path,     # legacy compat
                    "start": start,                       # final schema
                    "segment_start": start,               # legacy compat
                    "end": end,                           # final schema
                    "segment_end": end,                   # legacy compat
                    "duration": dur,                      # final schema
                    "speaker": speaker,                   # final schema
                    "dominant_speaker": sp_name,          # legacy compat
                    "speaker_overlap": {sp_name: dur} if sp_name != "UNKNOWN" else {},
                    "speaker_purity_score": 1.0 if sp_name != "UNKNOWN" else 0.0,
                    "transcript": transcript_text,
                    "language": result.get("language_code", "unknown"),
                    "transcription_confidence": float(result.get("confidence", 1.0)),
                    "quality_score": 1.0,
                    "emotion": "neutral",                 # updated by tagging step
                    "quality_issues": []
                }
                
                all_candidate_records.append(record)
                sliced_count += 1
                
                # Track in local speaker metadata
                if sp_name != "UNKNOWN":
                    if sp_name not in speaker_metadata:
                        speaker_metadata[sp_name] = []
                    speaker_metadata[sp_name].append({
                        "start": start,
                        "end": end
                    })
                    all_unique_speakers.add(sp_name)
                    total_turns += 1
                    
        # Update metadata speaker list in place
        video["speaker_data"] = speaker_metadata
        videos_processed += 1
        print(f"Generated {sliced_count} segments for: {title}")
        
    # Write segments_metadata.jsonl
    segments_path = ROOT_DIR / "data" / "segments_metadata.jsonl"
    segments_path.parent.mkdir(parents=True, exist_ok=True)
    with open(segments_path, "w", encoding="utf-8") as f:
        for r in all_candidate_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    print(f"\nGenerated {len(all_candidate_records)} total segment candidates in {segments_path}")
    save_stats(videos_processed, videos_failed, len(all_unique_speakers), total_turns)
    
    return metadata

def main():
    metadata_path = ROOT_DIR / "data" / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Required metadata file not found at: {metadata_path.resolve()}.\n"
            "Please ensure you run Step 1 (Metadata Ingestion & Audio Download) first."
        )
        
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    if not metadata:
        print("No videos found in metadata.json. Aborting.")
        return
        
    if TEST_MODE:
        print(f"\n[TEST MODE ACTIVE] Processing only the first video in metadata.json.")
        metadata_to_process = metadata[:1]
    else:
        metadata_to_process = metadata
        
    processed_metadata = diarize_audio(metadata_to_process)
    
    if TEST_MODE and processed_metadata:
        metadata[0] = processed_metadata[0]
        
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully updated metadata with diarization at: {metadata_path.resolve()}")

# if __name__ == "__main__":
#     main()