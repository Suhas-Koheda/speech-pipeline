---
license: cc-by-nc-4.0
language:
- te
tags:
- telugu
- speech
- telangana
- automatic-speech-recognition
---

# Telangana Speech Dataset

Telugu speech segments extracted from Telangana-focused YouTube podcasts and standup comedy videos.

## Dataset Structure

```
telangana-speech-dataset/
├── audio/
│   ├── segment_00001.wav
│   ├── segment_00002.wav
│   └── ...
├── metadata.jsonl
└── README.md
```

## Metadata Format

Each row in `metadata.jsonl`:

```json
{
  "audio": "audio/segment_00001.wav",
  "transcript": "తెలంగాణ ఉద్యమం...",
  "language": "te",
  "speaker": "unknown",
  "source": "youtube",
  "video_id": "6kPsgJHAXA0",
  "channel": "Raw Talks With VK",
  "start": 12.4,
  "end": 23.8
}
```

- **audio**: path to the audio file (16kHz mono WAV)
- **transcript**: ASR transcript (IndicConformer-600m multilingual)
- **language**: ISO 639-1 code (te = Telugu)
- **speaker**: unknown (multi-speaker, not diarized)
- **source**: source platform
- **video_id**: YouTube video ID
- **channel**: YouTube channel name
- **start/end**: segment timestamps in seconds

## Stats

| Total Segments |
|----------------|
| 953            |

## Sources

- Raw Talks With VK (Telugu Podcast)
- Venkat Blaze (Telugu Standup Comedy)
- ADVITAM MEDIA

## Notes

- Audio is 16kHz mono WAV, segmented via Silero VAD with 3-15s duration filter
- Transcripts generated using ai4bharat/indic-conformer-600m-multilingual
- Speaker diarization not yet applied
