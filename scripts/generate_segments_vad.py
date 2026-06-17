from extract_metatdata import collect_metadata
from download_audio import get_audio
import json
import re
from pathlib import Path

import soundfile as sf
from silero_vad import (
    load_silero_vad,
    read_audio,
    get_speech_timestamps,
)

SAMPLING_RATE = 16000

# TTS-optimized VAD configuration
MIN_SEGMENT_DURATION = 5.0
MAX_SEGMENT_DURATION = 20.0
MERGE_GAP_SECONDS = 0.5


def sanitize_name(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def merge_segments(
    timestamps,
    sampling_rate=SAMPLING_RATE,
    max_gap_seconds=MERGE_GAP_SECONDS,
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
    max_duration_seconds=MAX_SEGMENT_DURATION,
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
    min_duration_seconds=MIN_SEGMENT_DURATION,
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

    print(f"--- Segment Duration Statistics ---")
    print(f"Total Segments: {len(timestamps)}")
    print(f"Total Speech Duration: {sum(durations)/60:.2f} min ({sum(durations):.2f} sec)")
    print(f"Average Segment Duration: {sum(durations)/len(durations):.2f} sec")
    print(f"Max Segment Duration: {max(durations):.2f} sec")
    print(f"Min Segment Duration: {min(durations):.2f} sec")
    print(f"----------------------------------")


def save_segments(
    audio,
    timestamps,
    output_dir,
    video_metadata,
):
    video_id = video_metadata["video_id"]

    output_dir = Path(output_dir) / video_id

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    segment_metadata = []

    for idx, ts in enumerate(timestamps):
        start = ts["start"]
        end = ts["end"]

        segment = audio[start:end]

        segment_path = (
            output_dir /
            f"segment_{idx:05d}.wav"
        )

        sf.write(
            segment_path,
            segment.numpy(),
            SAMPLING_RATE,
        )

        duration = (end - start) / SAMPLING_RATE

        segment_metadata.append({
            "video_id": video_metadata["video_id"],
            "channel": video_metadata["channel"],
            "title": video_metadata["title"],
            "audio_path": video_metadata["audio_path"],
            "segment_path": str(segment_path),
            "start": start / SAMPLING_RATE,
            "end": end / SAMPLING_RATE,
            "duration": duration,
            "language": video_metadata.get("language", "unknown"),
            "quality_score": 1.0,
        })

    return segment_metadata


def process_audio(metadata):
    model = load_silero_vad()

    all_segment_metadata = []

    for video in metadata:
        try:
            print(
                f"\nProcessing: {video['title']}"
            )

            audio = read_audio(
                video["audio_path"],
                sampling_rate=SAMPLING_RATE,
            )

            speech_timestamps = (
                get_speech_timestamps(
                    audio,
                    model,
                )
            )

            print(
                f"Raw Segments: {len(speech_timestamps)}"
            )

            merged = merge_segments(
                speech_timestamps,
                max_gap_seconds=MERGE_GAP_SECONDS,
            )

            print(
                f"After Merge: {len(merged)}"
            )

            split_segments = (
                split_long_segments(
                    merged,
                    max_duration_seconds=MAX_SEGMENT_DURATION,
                )
            )

            print(
                f"After Split: {len(split_segments)}"
            )

            final_segments = (
                filter_segments(
                    split_segments,
                    min_duration_seconds=MIN_SEGMENT_DURATION,
                )
            )

            print(
                f"After Filter: {len(final_segments)}"
            )

            print_stats(final_segments)

            channel_name = sanitize_name(
                video["channel"]
            )

            output_dir = (
                Path("../segments")
                / channel_name
            )

            segment_metadata = save_segments(
                audio,
                final_segments,
                output_dir,
                video,
            )

            all_segment_metadata.extend(
                segment_metadata
            )

            print(
                f"Saved {len(segment_metadata)} segments"
            )

        except Exception as e:
            print(
                f"Failed: {video['title']}"
            )
            print(e)

    Path("../data").mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        "../data/segments_metadata.jsonl",
        "w",
        encoding="utf-8",
    ) as f:

        for record in all_segment_metadata:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"\nSaved {len(all_segment_metadata)} total segments"
    )


def main():
    with open(
        "../data/metadata.json",
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    process_audio(metadata)

# if __name__ == "__main__":
#     main()