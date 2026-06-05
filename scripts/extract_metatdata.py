from yt_dlp import YoutubeDL
from pathlib import Path
import json


def get_video_metadata(url: str):
    opts = {
        "quiet": True,
        "skip_download": True,
        "cookiesfrombrowser": ("chrome",),
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "video_id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("channel"),
        "duration": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "url": info.get("webpage_url"),
    }


def get_channel_videos(channel_url: str):
    opts = {
        "extract_flat": True,
        "quiet": True,
        "cookiesfrombrowser": ("chrome",),
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    videos = []

    for video in info.get("entries", []):
        if video and video.get("id"):
            videos.append(
                f"https://www.youtube.com/watch?v={video['id']}"
            )

    return videos


def is_channel_url(url: str):
    return any(
        x in url
        for x in [
            "/@",
            "/channel/",
            "/c/",
            "/user/",
        ]
    )


def read_links(file_path: str):
    urls = []

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()

            if line.startswith("https://"):
                urls.append(line)

    return urls


def collect_metadata(file_path: str):
    urls = read_links(file_path)

    all_video_urls = set()

    for url in urls:
        try:
            if is_channel_url(url):
                print(f"Expanding channel: {url}")

                channel_videos = get_channel_videos(url)

                print(
                    f"Found {len(channel_videos)} videos"
                )

                all_video_urls.update(channel_videos)

            else:
                all_video_urls.add(url)

        except Exception as e:
            print(f"Failed processing {url}")
            print(e)

    print(
        f"\nTotal unique videos: {len(all_video_urls)}\n"
    )

    metadata_list = []

    for idx, video_url in enumerate(all_video_urls, start=1):
        try:
            print(
                f"[{idx}/{len(all_video_urls)}] Extracting metadata"
            )

            metadata = get_video_metadata(video_url)

            metadata_list.append(metadata)

        except Exception as e:
            print(f"Failed metadata extraction")
            print(video_url)
            print(e)

    Path("../data").mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        "../data/metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata_list,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"\nSaved {len(metadata_list)} records to metadata.json"
    )


if __name__ == "__main__":
    collect_metadata(
        "/home/ssp/UnknownHaas/speech-pipeline/links.txt"
    )