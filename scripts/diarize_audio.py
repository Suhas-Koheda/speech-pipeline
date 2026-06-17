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
import soundfile as sf
from pathlib import Path
from dotenv import load_dotenv

# Ensure the scripts/ directory is in python search path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from sarvamai import SarvamAI

# Resolve project root path
ROOT_DIR = Path(__file__).resolve().parent.parent

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
            
        # Resolve path relative to project root
        if audio_path:
            abs_audio_path = ROOT_DIR / audio_path.replace("../", "")
        else:
            abs_audio_path = None
            
        if not abs_audio_path or not abs_audio_path.exists():
            print(f"Error: Audio file not found for video '{title}': {audio_path}")
            videos_failed += 1
            continue
            
        print(f"\nProcessing video: {title}")
        
        try:
            # 1. Get audio duration
            info = sf.info(abs_audio_path)
            duration = info.duration
            
            # 2. Call Sarvam Diarization via Batch API
            print("Creating batch speech-to-text job with diarization...")
            job = client.speech_to_text_job.create_job(
                model="saaras:v3",
                mode="transcribe",
                language_code="en-IN",  # universal English/multilingual code
                with_diarization=True
            )
            
            print(f"Uploading file: {abs_audio_path.name}")
            job.upload_files(file_paths=[str(abs_audio_path)])
            
            print("Starting batch job...")
            job.start()
            
            print("Waiting for job to complete (polling)...")
            job.wait_until_complete()
            
            # 3. Download and parse results
            speaker_metadata = {}
            num_speakers = 0
            num_turns = 0
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                job.download_outputs(output_dir=tmp_dir)
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
            
            # Progress log
            print(f"Progress Log - Video: '{title}'")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Speakers detected: {num_speakers}")
            print(f"  Turns detected: {num_turns}")
            
        except Exception as e:
            print(f"Error processing video '{title}': {e}")
            import traceback
            traceback.print_exc()
            videos_failed += 1
            
    # Write stats file
    save_stats(videos_processed, videos_failed, len(all_unique_speakers), total_turns)
    
    return metadata

if __name__ == "__main__":
    from download_audio import get_audio
    from extract_metatdata import collect_metadata
    
    # Run setup steps using absolute metadata path
    metadata_path = ROOT_DIR / "data" / "metadata.json"
    links_path = ROOT_DIR / "links.txt"
    
    # Perform download if files are missing or update metadata
    if links_path.exists():
        collect_metadata(str(links_path))
    else:
        print(f"Warning: {links_path} not found.")
        
    get_audio(str(metadata_path))
    
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            
        metadata = diarize_audio(metadata)
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
            
        print(f"Successfully updated metadata with diarization at: {metadata_path}")
    else:
        print(f"Error: {metadata_path} not found, cannot apply diarization.")