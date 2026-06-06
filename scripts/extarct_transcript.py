import json
import torch
import torchaudio
from transformers import AutoModel

MODEL_NAME = (
    "ai4bharat/indic-conformer-600m-multilingual"
)

TARGET_SR = 16000

model = AutoModel.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
)


def transcribe(
    audio_path,
    start_time,
    end_time,
):
    wav, sr = torchaudio.load(audio_path)

    wav = torch.mean(
        wav,
        dim=0,
        keepdim=True,
    )

    start_sample = int(
        start_time * sr
    )

    end_sample = int(
        end_time * sr
    )

    wav = wav[
        :,
        start_sample:end_sample,
    ]

    if sr != TARGET_SR:
        wav = torchaudio.transforms.Resample(
            sr,
            TARGET_SR,
        )(wav)

    transcript = model(
        wav,
        "te",
        "rnnt",
    )

    return transcript


def update_segments_metadata(
    metadata_path="../data/segments_metadata.jsonl",
):
    records = []

    with open(
        metadata_path,
        "r",
        encoding="utf-8",
    ) as f:
        for line in f:
            records.append(
                json.loads(line)
            )

    total = len(records)

    for idx, record in enumerate(
        records,
        start=1,
    ):
        try:
            transcript = transcribe(
                record["audio_path"],
                record["start"],
                record["end"],
            )

            record["transcript"] = transcript

            print(
                f"[{idx}/{total}] "
                f"{transcript[:50]}"
            )

        except Exception as e:
            print(
                f"Failed: {record['video_id']} "
                f"{record['start']}-{record['end']}"
            )
            print(e)

            record["transcript"] = ""

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as f:
        for record in records:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"\nUpdated {total} records"
    )


if __name__ == "__main__":
    update_segments_metadata()