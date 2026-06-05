from extract_metatdata import collect_metadata
import json
from yt_dlp import YoutubeDL
from pathlib import Path
import re

def sanitize_name(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)

def get_audio(metadata_file_path, output_dir):
    with open(metadata_file_path, 'r') as f:
        metadata = json.load(f)
    for video in metadata:
        try:
            if video["duration"] is None:
                continue

            if video["duration"] < 300:
                continue

            download_audio(
                video["url"],
                video["channel"],
                "mp3",
                output_dir
            )

        except Exception as e:
            print(f"Failed: {video['url']}")
            print(e)

def download_audio(video_url: str, channel_name: str, file_type: str,output_dir:str):
    channel_name = sanitize_name(channel_name)
    Path(f"{output_dir}/{channel_name}").mkdir(
        parents=True,
        exist_ok=True,
    )

    ydl_opts = {
        "format": "bestaudio/best" if file_type == "mp3" else "best",
        "outtmpl": f"{output_dir}/{channel_name}/%(title)s.%(ext)s",
        "download_archive": "downloaded.txt",
    }

    if file_type == "mp3":
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


if __name__=="__main__":
    collect_metadata(
        "/home/ssp/UnknownHaas/speech-pipeline/links.txt"
    )
    get_audio(
        "/home/ssp/UnknownHaas/speech-pipeline/data/metadata.json",
        "/home/ssp/UnknownHaas/speech-pipeline/audio"
    )
# https://www.youtube.com/watch?v=9QpkWAyG-eE&t=203s&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz
# https://www.youtube.com/watch?v=TdVWQ8jtZRM&t=1022s&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz
# https://www.youtube.com/watch?v=d6-IFzGisYQ&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz
# https://www.youtube.com/watch?v=XZqK-I-kc-Y&t=132s&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz0gcJCSgLAYcqIYzv
# https://www.youtube.com/watch?v=7FbeLGB6lr0&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz
# https://www.youtube.com/watch?v=mkPWFBmCpw8&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz


# channels
# https://www.youtube.com/@Telanganavillagefood/videos





# standup-comedy