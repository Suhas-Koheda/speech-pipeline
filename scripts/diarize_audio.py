from download_audio import get_audio
from extract_metatdata import collect_metadata
import torch
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
import json
pipeline=Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    
).to(torch.device("cpu"))

def diarize_audio(metadata):
    for video in metadata:
        print(f"Processing video {video['title']}")
        speaker_metadata={}
        with ProgressHook() as hook:
            output = pipeline(video["audio_path"], hook=hook)  
        
        for turn, speaker in output.speaker_diarization:
            if speaker not in speaker_metadata:
                speaker_metadata[speaker]=[]
            speaker_metadata[speaker].append(
                {
                    "start":turn.start,
                    "end":turn.end
                }
            )
        video["speaker_data"] = speaker_metadata
    return metadata


if __name__ == "__main__":
    collect_metadata(
        "../links.txt"
    )

    get_audio(
        "../data/metadata.json"
    )

    with open(
        "../data/metadata.json",
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    metadata = diarize_audio(
        metadata
    )

    with open(
        "../data/metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=4,
        )