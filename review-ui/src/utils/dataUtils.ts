import type { ReviewItem, ReviewAnnotation, ExportFormat, ExportScope, FilterState } from '../types';

// ─── Export ──────────────────────────────────────────────────────────────────

function scopeItems(
  items: ReviewItem[],
  scope: ExportScope,
  filteredIds?: Set<string>
): ReviewItem[] {
  switch (scope) {
    case 'approved':
      return items.filter((i) => i.annotation.review_status === 'accepted');
    case 'rejected':
      return items.filter((i) => i.annotation.review_status === 'rejected');
    case 'reviewed':
      return items.filter((i) => i.annotation.review_status !== 'unreviewed');
    case 'filtered':
      return filteredIds ? items.filter((i) => filteredIds.has(i.id)) : items;
    default:
      return items;
  }
}

function annotationToExport(item: ReviewItem) {
  const { segment, annotation } = item;
  return {
    // Original pipeline fields
    video_id: segment.video_id,
    channel: segment.channel,
    title: segment.title,
    segment_path: segment.segment_path,
    start: segment.start,
    end: segment.end,
    duration: segment.duration,
    language: segment.language,
    dominant_speaker: segment.dominant_speaker,
    emotion: segment.emotion,
    style: segment.style,

    // Review annotations
    original_transcript: annotation.original_transcript,
    corrected_transcript: annotation.corrected_transcript,
    transcript_was_corrected: annotation.corrected_transcript !== annotation.original_transcript,
    review_status: annotation.review_status,
    rejection_reason: annotation.rejection_reason ?? null,
    transcript_score: annotation.transcript_score ?? null,
    audio_quality_score: annotation.audio_quality_score ?? null,
    wrong_words: annotation.wrong_words.map(({ asr, correct }) => ({ asr, correct })),
    error_categories: annotation.error_categories,
    notes: annotation.notes,
    reviewed_at: annotation.reviewed_at ?? null,
  };
}

export function exportData(
  items: ReviewItem[],
  format: ExportFormat,
  scope: ExportScope,
  filteredIds?: Set<string>
): void {
  const selected = scopeItems(items, scope, filteredIds);
  const rows = selected.map(annotationToExport);

  if (format === 'json') {
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `speech_review_${scope}_${timestamp()}.json`);
  } else {
    const csv = toCsv(rows);
    const blob = new Blob([csv], { type: 'text/csv' });
    downloadBlob(blob, `speech_review_${scope}_${timestamp()}.csv`);
  }
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function timestamp(): string {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

function toCsv(rows: ReturnType<typeof annotationToExport>[]): string {
  if (rows.length === 0) return '';
  const keys = Object.keys(rows[0]);
  const header = keys.join(',');
  const body = rows.map((row) =>
    keys
      .map((k) => {
        const val = (row as Record<string, unknown>)[k];
        const str = Array.isArray(val) ? JSON.stringify(val) : String(val ?? '');
        return `"${str.replace(/"/g, '""')}"`;
      })
      .join(',')
  );
  return [header, ...body].join('\n');
}

// ─── Import ──────────────────────────────────────────────────────────────────

export async function parseImportFile(file: File): Promise<ReviewAnnotation[]> {
  const text = await file.text();

  if (file.name.endsWith('.json')) {
    const data = JSON.parse(text);
    const arr = Array.isArray(data) ? data : [data];
    return arr.map(normalizeAnnotation).filter(Boolean) as ReviewAnnotation[];
  }

  if (file.name.endsWith('.jsonl')) {
    return text
      .split('\n')
      .filter((l) => l.trim())
      .map((l) => {
        try {
          return normalizeAnnotation(JSON.parse(l));
        } catch {
          return null;
        }
      })
      .filter(Boolean) as ReviewAnnotation[];
  }

  throw new Error('Unsupported file format. Use .json or .jsonl');
}

function normalizeAnnotation(raw: Record<string, unknown>): ReviewAnnotation | null {
  if (!raw.segment_id && !raw.video_id) return null;

  const segmentId = (raw.segment_id as string) ?? `${raw.video_id}__${Number(raw.start).toFixed(3)}`;

  return {
    segment_id: segmentId,
    original_transcript: (raw.original_transcript as string) ?? '',
    corrected_transcript: (raw.corrected_transcript as string) ?? (raw.original_transcript as string) ?? '',
    review_status: (raw.review_status as ReviewAnnotation['review_status']) ?? 'unreviewed',
    rejection_reason: raw.rejection_reason as ReviewAnnotation['rejection_reason'],
    transcript_score: typeof raw.transcript_score === 'number' ? raw.transcript_score : undefined,
    audio_quality_score: typeof raw.audio_quality_score === 'number' ? raw.audio_quality_score : undefined,
    wrong_words: Array.isArray(raw.wrong_words)
      ? (raw.wrong_words as { asr: string; correct: string }[]).map((w, i) => ({
          id: `imported-${i}`,
          asr: w.asr,
          correct: w.correct,
        }))
      : [],
    error_categories: Array.isArray(raw.error_categories)
      ? (raw.error_categories as ReviewAnnotation['error_categories'])
      : [],
    notes: (raw.notes as string) ?? '',
    reviewed_at: raw.reviewed_at as string | undefined,
  };
}

// ─── Diff ────────────────────────────────────────────────────────────────────

export interface DiffToken {
  text: string;
  type: 'equal' | 'insert' | 'delete';
}

export function wordDiff(original: string, corrected: string): DiffToken[] {
  const origWords = original.split(/\s+/);
  const corrWords = corrected.split(/\s+/);

  // Simple LCS-based diff
  const m = origWords.length;
  const n = corrWords.length;

  // DP table
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (origWords[i - 1] === corrWords[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Traceback
  const result: DiffToken[] = [];
  let i = m,
    j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origWords[i - 1] === corrWords[j - 1]) {
      result.unshift({ text: origWords[i - 1], type: 'equal' });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ text: corrWords[j - 1], type: 'insert' });
      j--;
    } else {
      result.unshift({ text: origWords[i - 1], type: 'delete' });
      i--;
    }
  }

  return result;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

import type { AnalyticsData } from '../types';

export function computeAnalytics(items: ReviewItem[]): AnalyticsData {
  const total = items.length;
  const approved = items.filter((i) => i.annotation.review_status === 'accepted').length;
  const rejected = items.filter((i) => i.annotation.review_status === 'rejected').length;
  const skipped = items.filter((i) => i.annotation.review_status === 'skipped').length;
  const unreviewed = items.filter((i) => i.annotation.review_status === 'unreviewed').length;
  const reviewed = total - unreviewed;
  const remaining = unreviewed;
  const approvalRate = reviewed > 0 ? (approved / reviewed) * 100 : 0;

  const scoredTranscripts = items.filter((i) => i.annotation.transcript_score != null);
  const avgTranscriptScore =
    scoredTranscripts.length > 0
      ? scoredTranscripts.reduce((s, i) => s + (i.annotation.transcript_score ?? 0), 0) /
        scoredTranscripts.length
      : 0;

  const scoredAudio = items.filter((i) => i.annotation.audio_quality_score != null);
  const avgAudioScore =
    scoredAudio.length > 0
      ? scoredAudio.reduce((s, i) => s + (i.annotation.audio_quality_score ?? 0), 0) /
        scoredAudio.length
      : 0;

  const corrected = items.filter(
    (i) => i.annotation.corrected_transcript !== i.annotation.original_transcript
  ).length;
  const correctionRate = reviewed > 0 ? (corrected / reviewed) * 100 : 0;

  // Rejection reasons
  const rejectionReasonCounts: Record<string, number> = {};
  for (const item of items) {
    const reason = item.annotation.rejection_reason;
    if (reason) rejectionReasonCounts[reason] = (rejectionReasonCounts[reason] ?? 0) + 1;
  }

  // Error categories
  const errorCategoryCounts: Record<string, number> = {};
  for (const item of items) {
    for (const cat of item.annotation.error_categories) {
      errorCategoryCounts[cat] = (errorCategoryCounts[cat] ?? 0) + 1;
    }
  }

  // ASR errors aggregated
  const asrMap: Record<string, { asr: string; correct: string; count: number }> = {};
  for (const item of items) {
    for (const w of item.annotation.wrong_words) {
      const key = `${w.asr}→${w.correct}`;
      if (!asrMap[key]) asrMap[key] = { asr: w.asr, correct: w.correct, count: 0 };
      asrMap[key].count++;
    }
  }
  const asrErrors = Object.values(asrMap)
    .sort((a, b) => b.count - a.count)
    .slice(0, 50);

  // Distributions
  const languageDist: Record<string, number> = {};
  const emotionDist: Record<string, number> = {};
  const speakerDist: Record<string, number> = {};
  const channelDist: Record<string, number> = {};

  for (const item of items) {
    const seg = item.segment;
    languageDist[seg.language] = (languageDist[seg.language] ?? 0) + 1;
    if (seg.emotion) emotionDist[seg.emotion] = (emotionDist[seg.emotion] ?? 0) + 1;
    const spk = seg.dominant_speaker ?? seg.speaker ?? 'unknown';
    speakerDist[spk] = (speakerDist[spk] ?? 0) + 1;
    channelDist[seg.channel] = (channelDist[seg.channel] ?? 0) + 1;
  }

  // Duration buckets
  const buckets = [
    { min: 0, max: 3, label: '0-3s' },
    { min: 3, max: 6, label: '3-6s' },
    { min: 6, max: 10, label: '6-10s' },
    { min: 10, max: 15, label: '10-15s' },
    { min: 15, max: Infinity, label: '15s+' },
  ];
  const durationBuckets = buckets.map((b) => ({
    range: b.label,
    count: items.filter((i) => i.segment.duration >= b.min && i.segment.duration < b.max).length,
  }));

  // Daily progress
  const dailyMap: Record<string, { reviewed: number; approved: number }> = {};
  for (const item of items) {
    const at = item.annotation.reviewed_at;
    if (at) {
      const date = at.slice(0, 10);
      if (!dailyMap[date]) dailyMap[date] = { reviewed: 0, approved: 0 };
      dailyMap[date].reviewed++;
      if (item.annotation.review_status === 'accepted') dailyMap[date].approved++;
    }
  }
  const dailyProgress = Object.entries(dailyMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, v]) => ({ date, ...v }));

  // Accepted-only duration stats
  const acceptedItems = items.filter((i) => i.annotation.review_status === 'accepted');
  const totalAcceptedDuration = acceptedItems.reduce((sum, i) => sum + i.segment.duration, 0);

  const acceptedDurationPerLanguage: Record<string, number> = {};
  for (const item of acceptedItems) {
    const lang = item.segment.language;
    acceptedDurationPerLanguage[lang] = (acceptedDurationPerLanguage[lang] ?? 0) + item.segment.duration;
  }

  return {
    total,
    reviewed,
    approved,
    rejected,
    skipped,
    remaining,
    approvalRate,
    avgTranscriptScore,
    avgAudioScore,
    correctionRate,
    rejectionReasonCounts,
    errorCategoryCounts,
    asrErrors,
    languageDist,
    emotionDist,
    speakerDist,
    channelDist,
    durationBuckets,
    dailyProgress,
    totalAcceptedDuration,
    acceptedDurationPerLanguage,
  };
}

// ─── JSONL parser ─────────────────────────────────────────────────────────────

import type { PipelineSegment } from '../types';

export async function parseJsonlFile(file: File): Promise<PipelineSegment[]> {
  const text = await file.text();
  const segments: PipelineSegment[] = [];

  const lines = text.split('\n').filter((l) => l.trim());
  for (const line of lines) {
    try {
      segments.push(JSON.parse(line) as PipelineSegment);
    } catch {
      // skip malformed lines
    }
  }

  return segments;
}

export function filterUniqueSegments(_filters: FilterState, allFiltered: ReturnType<typeof scopeItems>): Set<string> {
  return new Set(allFiltered.map((i) => i.id));
}
