import torch
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
import json
pipeline=Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    
).to(torch.device("cpu"))

def diarize_audio(segment_data):
    for segment in segment_data:
        print(f"Processing segment {segment['segment_path']}")
        speaker_metadata={}
        with ProgressHook() as hook:
            output = pipeline(segment["segment_path"], hook=hook)  
        
        for turn, speaker in output.speaker_diarization:
            if speaker not in speaker_metadata:
                speaker_metadata[speaker]=[]
            speaker_metadata[speaker].append(
                {
                    "start":turn.start,
                    "end":turn.end
                }
            )
        segment["speaker_data"] = speaker_metadata
    return segment_data


if __name__ == "__main__":
    with open(
        "../data/segments_metadata.jsonl",
        "r",
        encoding="utf-8",
    ) as f:
        segment_data = [
            json.loads(line)
            for line in f
        ]
    segment_data = diarize_audio(segment_data)
    with open(
        "../data/segments_metadata.jsonl",
        "w",
        encoding="utf-8",
    ) as f:
        for record in segment_data:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )