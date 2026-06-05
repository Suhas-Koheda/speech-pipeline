from pathlib import Path
from yt_dlp import YoutubeDL


def get_video_urls(channel_url: str):
    opts = {
        "extract_flat": True,
        "quiet": True,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    channel_name = (
        info.get("channel")
        or info.get("uploader")
        or info.get("title")
        or "unknown_channel"
    )

    videos = [
        f"https://www.youtube.com/watch?v={video['id']}"
        for video in info.get("entries", [])
        if video
    ]

    return channel_name, videos


from pathlib import Path
from yt_dlp import YoutubeDL


def download_audio(video_url: str, channel_name: str, file_type: str):
    Path(f"downloads/{channel_name}").mkdir(
        parents=True,
        exist_ok=True,
    )

    ydl_opts = {
        "format": "bestaudio/best" if file_type == "mp3" else "best",
        "outtmpl": f"downloads/{channel_name}/%(title)s.%(ext)s",
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
        
def download_channel(channel_url: str):
    channel_name, video_urls = get_video_urls(channel_url)

    print(f"Channel: {channel_name}")
    print(f"Found {len(video_urls)} videos")

    for idx, url in enumerate(video_urls, start=1):
        print(f"[{idx}/{len(video_urls)}]")
        download_audio(url, channel_name)

if __name__ == "__main__":
    download_channel(
        "https://www.youtube.com/@Telanganavillagefood/videos"
    )