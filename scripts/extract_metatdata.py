from yt_dlp import YoutubeDL
def get_video_metadata(url:str):
    opts={
        "quiet":True,
        "skip_download":True,
        "cookiesfrombrowser": ("chrome",),
    }
    with YoutubeDL(opts) as ydl:
        info=ydl.extract_info(url,download=False)
    return {
        "video_id":info.get("id"),
        "title":info.get("title"),
        "channel":info.get("channel"),
        "duration":info.get("duration"),
        "upload_date":info.get("upload_date"),
        "url":info.get("webpage_url")
    }


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=WlfKz2bgNSA"

    metadata = get_video_metadata(url)

    for key, value in metadata.items():
        print(f"{key}: {value}")