from pathlib import Path
import re

import soundfile as sf
from silero_vad import (
    load_silero_vad,
    read_audio,
    get_speech_timestamps,
)

SAMPLING_RATE = 16000


def sanitize_name(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def merge_segments(
    timestamps,
    sampling_rate=SAMPLING_RATE,
    max_gap_seconds=0.5,
):
    max_gap = int(max_gap_seconds * sampling_rate)

    if not timestamps:
        return []

    merged = [timestamps[0].copy()]

    for current in timestamps[1:]:
        previous = merged[-1]

        gap = current["start"] - previous["end"]

        if gap <= max_gap:
            previous["end"] = current["end"]
        else:
            merged.append(current.copy())

    return merged


def split_long_segments(
    timestamps,
    sampling_rate=SAMPLING_RATE,
    max_duration_seconds=15,
):
    max_samples = int(
        max_duration_seconds * sampling_rate
    )

    result = []

    for ts in timestamps:
        start = ts["start"]
        end = ts["end"]

        while end - start > max_samples:
            result.append({
                "start": start,
                "end": start + max_samples,
            })

            start += max_samples

        if end > start:
            result.append({
                "start": start,
                "end": end,
            })

    return result


def filter_segments(
    timestamps,
    sampling_rate=SAMPLING_RATE,
    min_duration_seconds=3.0,
):
    filtered = []

    for ts in timestamps:
        duration = (
            ts["end"] - ts["start"]
        ) / sampling_rate

        if duration >= min_duration_seconds:
            filtered.append(ts)

    return filtered


def print_stats(timestamps):
    if not timestamps:
        print("No segments found")
        return

    durations = [
        (ts["end"] - ts["start"]) / SAMPLING_RATE
        for ts in timestamps
    ]

    print(f"Segments: {len(timestamps)}")
    print(f"Speech Duration: {sum(durations)/60:.2f} min")
    print(f"Average: {sum(durations)/len(durations):.2f} sec")
    print(f"Max: {max(durations):.2f} sec")
    print(f"Min: {min(durations):.2f} sec")


def save_segments(
    audio,
    timestamps,
    output_dir,
    video_title,
):
    video_title = sanitize_name(video_title)

    output_dir = Path(output_dir) / video_title

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for idx, ts in enumerate(timestamps):
        start = ts["start"]
        end = ts["end"]

        segment = audio[start:end]

        sf.write(
            output_dir / f"segment_{idx:05d}.wav",
            segment.numpy(),
            SAMPLING_RATE,
        )


def process_audio(
    audio_path,
    output_dir,
    video_title,
):
    print("Loading audio...")

    audio = read_audio(
        audio_path,
        sampling_rate=SAMPLING_RATE,
    )

    print("Loading VAD model...")

    model = load_silero_vad()

    print("Running VAD...")

    speech_timestamps = get_speech_timestamps(
        audio,
        model,
    )

    print(
        f"Raw Segments: {len(speech_timestamps)}"
    )

    merged = merge_segments(
        speech_timestamps,
        max_gap_seconds=0.5,
    )

    print(
        f"After Merge: {len(merged)}"
    )

    split_segments = split_long_segments(
        merged,
        max_duration_seconds=15,
    )

    print(
        f"After Split: {len(split_segments)}"
    )

    final_segments = filter_segments(
        split_segments,
        min_duration_seconds=3.0,
    )

    print(
        f"After Filter: {len(final_segments)}"
    )

    print_stats(final_segments)

    print("Saving segments...")

    save_segments(
        audio,
        final_segments,
        output_dir,
        video_title,
    )

    print(
        f"Saved to {output_dir}"
    )


if __name__ == "__main__":
    process_audio(
        "/home/ssp/UnknownHaas/speech-pipeline/audio/Raw Talks With VK/You Might Cry Watching🥺｜Manaki Teliyani History｜ Ft.Pasham Yadagiri｜RawTalks withVK TeluguPodcast 64.mp3",
        "/home/ssp/UnknownHaas/speech-pipeline/segments/Raw Talks With VK",
        "You Might Cry Watching🥺｜Manaki Teliyani History｜ Ft.Pasham Yadagiri｜RawTalks withVK TeluguPodcast 64",
    )