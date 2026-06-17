# Speech Review UI

Production-grade Speech Dataset Review & Curation Platform for the Sarvam AI TTS dataset curation assignment.

## Quick Start

```bash
cd review-ui
npm install
npm run dev
```

Opens at **http://localhost:5173**

## Workflow

1. **Import Dataset** → Go to `/data` → drag-and-drop `segments_metadata_final.jsonl`
2. **Review** → Navigate to `/` → use keyboard shortcuts to blaze through samples
3. **Export** → `Ctrl+S` or `/data` → export JSON/CSV for final submission

## Audio Path Resolution

The audio files use relative paths like `../segments/…`. Since the browser can't read the local filesystem directly, serve the parent directory with:

```bash
# From the speech-pipeline root
python3 -m http.server 8080
```

Then in your JSONL, paths like `../segments/TEDx Talks/…` will resolve via the Vite proxy (see below).

### Vite proxy (optional)

Add to `vite.config.ts` to proxy audio requests:

```ts
server: {
  proxy: {
    '/audio': {
      target: 'http://localhost:8080',
      rewrite: (path) => path.replace(/^\/audio/, '')
    }
  }
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `A` | Accept sample |
| `R` | Reject sample |
| `S` | Skip sample |
| `←/→` | Navigate samples |
| `1-5` | Transcript score |
| `Shift+1-5` | Audio quality score |
| `T` | Focus transcript editor |
| `N` | Focus notes |
| `Ctrl+S` | Export |
| `?` | Shortcut help |

## Tech Stack

- React 18 + TypeScript + Vite
- Tailwind CSS v3 (dark glassmorphism theme)
- Zustand + localStorage persistence (autosave)
- TanStack Virtual (handles 5000+ segments without lag)
- WaveSurfer.js (waveform visualization)
- Recharts (analytics dashboard)
- React Router v6

## Export Format

Each exported record contains the full pipeline metadata plus:

```json
{
  "original_transcript": "...",
  "corrected_transcript": "...",
  "transcript_was_corrected": true,
  "review_status": "accepted",
  "rejection_reason": null,
  "transcript_score": 5,
  "audio_quality_score": 4,
  "wrong_words": [{ "asr": "గురుంచి", "correct": "గురించి" }],
  "error_categories": ["spelling"],
  "notes": "...",
  "reviewed_at": "2026-06-17T..."
}
```
