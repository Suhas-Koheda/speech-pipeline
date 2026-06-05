from scripts.download_videos import download_audio
import json

def get_audio(metadata_file_path, output_dir):
    with open(metadata_file_path, 'r') as f:
        metadata = json.load(f)
    for video in metadata:
        if video["duration"] is None:
            continue

        if video["duration"] < 300:
            continue

        download_audio(
            video["url"],
            video["channel"],
            "mp3"
        )