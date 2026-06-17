"""
Speaker Diarization using Sarvam Diarization Batch API.

Replaces the local PyAnnote engine with Sarvam's cloud diarization service.
Outputs speaker segment intervals in standard speaker_data format to metadata.json
and saves the raw Sarvam response to data/sarvam_transcripts.json.
"""

import sys
import os
import json
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

def diarize_audio(metadata):
    # Stats tracking
    videos_processed = 0
    videos_failed = 0
    all_unique_speakers = set()
    total_turns = 0
    
    # Initialize Sarvam client
    load_dotenv()
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("Error: SARVAM_API_KEY not found in environment variables.")
        save_stats(0, len(metadata), 0, 0)
        return metadata
        
    client = SarvamAI(api_subscription_key=api_key)
    
    for video in metadata:
        title = video.get("title", "Unknown Video")
        audio_path = video.get("audio_path")
        video_id = video.get("video_id")
        
        if not video_id:
            print(f"Error: video_id is missing for video: {title}")
            videos_failed += 1
            continue
            
        # Check if already processed and skip
        if "speaker_data" in video and video["speaker_data"]:
            print(f"Skipping already processed video: {title}")
            for sp_name, turns in video["speaker_data"].items():
                all_unique_speakers.add(sp_name)
                total_turns += len(turns)
            videos_processed += 1
            continue
            
        # Resolve path relative to project root
        if audio_path:
            abs_audio_path = ROOT_DIR / audio_path.replace("../", "")
        else:
            abs_audio_path = None
            
        if not abs_audio_path or not abs_audio_path.exists():
            print(f"Error: Audio file not found for video '{title}': {audio_path}")
            videos_failed += 1
            continue
            
        # Debugging logs before upload (Issue 2)
        file_size_bytes = abs_audio_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        print(f"\n--- Investigating Audio File for Upload ---")
        print(f"Video Title: {title}")
        print(f"Audio Path: {abs_audio_path}")
        print(f"Audio Path Absolute: {abs_audio_path.resolve()}")
        print(f"File Exists: {abs_audio_path.exists()}")
        print(f"File Size: {file_size_bytes} bytes ({file_size_mb:.2f} MB)")
        print(f"----------------------------------------")
        
        try:
            # Get audio duration
            info = sf.info(abs_audio_path)
            duration = info.duration
            
            # Use a temporary directory and symlink to ensure an ASCII-only filename is sent to Sarvam API
            with tempfile.TemporaryDirectory() as upload_tmp_dir:
                temp_audio_path = Path(upload_tmp_dir) / f"{video_id}.wav"
                try:
                    os.symlink(abs_audio_path.resolve(), temp_audio_path)
                    print(f"Created temporary symlink for upload: {temp_audio_path}")
                except Exception as sym_err:
                    print(f"Symlink failed ({sym_err}). Copying file instead...")
                    import shutil
                    shutil.copy(abs_audio_path, temp_audio_path)
                
                # Call Sarvam Diarization via Batch API with retries
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
                print(f"Upload success response: {upload_success}")
                
                # Validation before job start (Issue 4)
                if not upload_success:
                    raise ValueError("No files were uploaded to Sarvam. Aborting job.")
                    
                print("Starting batch job...")
                retry_api_call(job.start)
                
                print("Waiting for job to complete (polling)...")
                retry_api_call(job.wait_until_complete)
                
                # Download and parse results
                speaker_metadata = {}
                num_speakers = 0
                num_turns = 0
                
                with tempfile.TemporaryDirectory() as tmp_dir:
                    print("Downloading outputs...")
                    retry_api_call(job.download_outputs, output_dir=tmp_dir)
                    json_files = glob.glob(os.path.join(tmp_dir, "*.json"))
                    if not json_files:
                        raise ValueError("Failed to download or find results JSON.")
                        
                    with open(json_files[0], "r", encoding="utf-8") as f:
                        result = json.load(f)
                    
                    # Save raw response for ASR reuse
                    save_transcript_response(video_id, result)
                        
                    # Extract entries
                    entries = []
                    if "diarized_transcript" in result:
                        entries = result["diarized_transcript"].get("entries", [])
                    elif "entries" in result:
                        entries = result["entries"]
                        
                    # Group into PyAnote speaker_data format
                    for entry in entries:
                        sp_id = entry.get("speaker_id", "0")
                        # Format to SPEAKER_XX
                        try:
                            sp_name = f"SPEAKER_{int(sp_id):02d}"
                        except ValueError:
                            sp_name = f"SPEAKER_{sp_id}"
                            
                        start = float(entry.get("start_time_seconds", 0.0))
                        end = float(entry.get("end_time_seconds", 0.0))
                        
                        if sp_name not in speaker_metadata:
                            speaker_metadata[sp_name] = []
                        speaker_metadata[sp_name].append({
                            "start": start,
                            "end": end
                        })
                        all_unique_speakers.add(sp_name)
                        num_turns += 1
                        total_turns += 1
                        
                    num_speakers = len(speaker_metadata)
                    
                # Store in video metadata
                video["speaker_data"] = speaker_metadata
                videos_processed += 1
                
                # Get final status of job for logging
                final_status = retry_api_call(job.get_status)
                
                # Transcript & Diarization details
                has_transcripts = "No"
                has_diarization = "No"
                if entries:
                    has_transcripts = f"Yes ({len(entries)} entries)"
                    if any(entry.get("speaker_id") is not None for entry in entries):
                        has_diarization = "Yes"
                        
                # Improved logging (Issue 5)
                print(f"\n==================================================")
                print(f"Video title:          {title}")
                print(f"Audio path:           {abs_audio_path}")
                print(f"File size MB:         {file_size_mb:.2f} MB")
                print(f"Upload success:       {upload_success}")
                print(f"Job ID:               {job.job_id}")
                print(f"Job status:           {final_status.job_state}")
                print(f"Transcript status:    {has_transcripts}")
                print(f"Diarization status:   {has_diarization}")
                print(f"==================================================\n")
            
        except Exception as e:
            print(f"Error processing video '{title}': {e}")
            import traceback
            traceback.print_exc()
            videos_failed += 1
            
    # Write stats file
    save_stats(videos_processed, videos_failed, len(all_unique_speakers), total_turns)
    
    return metadata

def main():
    # Validation: metadata.json must exist (Issue 1)
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
        
    # Small-file test mode (Issue 6)
    if TEST_MODE:
        print(f"\n[TEST MODE ACTIVE] Processing only the first video in metadata.json.")
        metadata_to_process = metadata[:1]
    else:
        metadata_to_process = metadata
        
    processed_metadata = diarize_audio(metadata_to_process)
    
    # Merge test results back into original metadata if test mode was active
    if TEST_MODE and processed_metadata:
        metadata[0] = processed_metadata[0]
        
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully updated metadata with diarization at: {metadata_path.resolve()}")

# if __name__ == "__main__":
#     main()