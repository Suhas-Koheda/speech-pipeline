import json


def overlap(
    seg_start,
    seg_end,
    turn_start,
    turn_end,
):
    return max(
        0,
        min(seg_end, turn_end)
        - max(seg_start, turn_start),
    )


def assign_speakers():
    with open(
        "../data/metadata.json",
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    speaker_lookup = {
        video["video_id"]: video.get(
            "speaker_data",
            {},
        )
        for video in metadata
    }

    updated = []

    with open(
        "../data/segments_metadata.jsonl",
        "r",
        encoding="utf-8",
    ) as f:
        for idx, line in enumerate(
            f,
            start=1,
        ):
            segment = json.loads(line)

            speaker_data = speaker_lookup.get(
                segment["video_id"],
                {},
            )

            speaker_overlap = {}

            for speaker, turns in speaker_data.items():
                total = 0

                for turn in turns:
                    total += overlap(
                        segment["start"],
                        segment["end"],
                        turn["start"],
                        turn["end"],
                    )

                if total > 0:
                    speaker_overlap[speaker] = round(
                        total,
                        3,
                    )

            if speaker_overlap:
                sorted_speakers = sorted(
                    speaker_overlap.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )

                if len(sorted_speakers) >= 2:
                    first_overlap = (
                        sorted_speakers[0][1]
                    )
                    second_overlap = (
                        sorted_speakers[1][1]
                    )

                    if (
                        first_overlap > 0
                        and second_overlap
                        / first_overlap
                        > 0.8
                    ):
                        dominant_speaker = (
                            "MIXED"
                        )
                    else:
                        dominant_speaker = (
                            sorted_speakers[0][0]
                        )
                else:
                    dominant_speaker = (
                        sorted_speakers[0][0]
                    )
            else:
                dominant_speaker = "UNKNOWN"

            # Calculate speaker purity score
            segment_duration = segment["end"] - segment["start"]
            if speaker_overlap and dominant_speaker not in ["MIXED", "UNKNOWN"]:
                dominant_overlap = speaker_overlap.get(dominant_speaker, 0)
                speaker_purity_score = min(dominant_overlap / segment_duration, 1.0)
            else:
                speaker_purity_score = 0.0

            segment["dominant_speaker"] = (
                dominant_speaker
            )
            segment["speaker_overlap"] = (
                speaker_overlap
            )
            segment["speaker_purity_score"] = round(speaker_purity_score, 3)

            updated.append(segment)

            if idx % 100 == 0:
                print(
                    f"Processed {idx} segments"
                )

    with open(
        "../data/segments_metadata.jsonl",
        "w",
        encoding="utf-8",
    ) as f:
        for segment in updated:
            f.write(
                json.dumps(
                    segment,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"\nUpdated {len(updated)} segments"
    )


if __name__ == "__main__":
    assign_speakers()