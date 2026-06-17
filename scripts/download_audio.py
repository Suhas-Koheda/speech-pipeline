from extract_metatdata import collect_metadata
import json
from yt_dlp import YoutubeDL
from pathlib import Path
import re


AUDIO_DIR = Path("../audio")


def sanitize_name(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def download_audio(
    video_url: str,
    channel_name: str,
    title: str,
):
    channel_name = sanitize_name(channel_name)
    title = sanitize_name(title)

    channel_dir = AUDIO_DIR / channel_name

    channel_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": str(
        channel_dir / "%(title)s.%(ext)s"
    ),
    "download_archive": "downloaded.txt",
    "cookiesfrombrowser": ("chrome",),
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        }
    ],
    "postprocessor_args": [
        "-ar", "16000",
        "-ac", "1",
    ],
}


    extract_opts = ydl_opts.copy()
    extract_opts.pop("download_archive", None)

    with YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(
            video_url,
            download=False,
        )
        filename = Path(
            ydl.prepare_filename(info)
        ).stem + ".wav"

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    relative_audio_path = str(
        AUDIO_DIR
        / channel_name
        / filename
    )

    return relative_audio_path


def get_audio(
    metadata_file_path,
):
    with open(
        metadata_file_path,
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    updated_metadata = []

    for video in metadata:
        try:
            if video["duration"] is None:
                continue

            if video["duration"] < 300:
                continue

            audio_path = download_audio(
                video["url"],
                video["channel"],
                video["title"],
            )

            video["audio_path"] = audio_path

            updated_metadata.append(video)

            print(
                f"Downloaded: {video['title']}"
            )

        except Exception as e:
            print(
                f"Failed: {video['url']}"
            )
            import traceback
            traceback.print_exc()

    with open(
        metadata_file_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            updated_metadata,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"Updated metadata saved to {metadata_file_path}"
    )


def main():
    collect_metadata(
        "../links.txt"
    )
    get_audio(
        "../data/metadata.json"
    )

# if __name__ == "__main__":
#     main()
# https://www.youtube.com/watch?v=9QpkWAyG-eE&t=203s&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz
# https://www.youtube.com/watch?v=TdVWQ8jtZRM&t=1022s&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz

# https://www.youtube.com/watch?v=7FbeLGB6lr0&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz
# https://www.youtube.com/watch?v=mkPWFBmCpw8&pp=ygUSdGVsYW5nYW5hIHBvZGNhc3Rz


# channels
# https://www.youtube.com/@Telanganavillagefood/videos





# standup-comedy