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