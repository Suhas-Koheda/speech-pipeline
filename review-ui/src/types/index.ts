// ============================================================
// Raw pipeline segment (from JSONL)
// ============================================================
export interface PipelineSegment {
  video_id: string;
  channel: string;
  title: string;
  audio_path?: string;
  segment_path: string;
  start: number;
  segment_start?: number;
  end: number;
  segment_end?: number;
  duration: number;
  speaker?: string;
  dominant_speaker?: string;
  speaker_overlap?: Record<string, number>;
  speaker_purity_score?: number;
  transcript: string;
  language: string;
  transcription_confidence?: number;
  quality_score?: number;
  emotion?: string;
  quality_issues?: string[];
  style?: string;
  style_confidence?: number;
  emotion_confidence?: number;
  repetition_rate?: number;
  validation_status?: string;
  rejection_reasons?: string[];
}

// ============================================================
// Review status
// ============================================================
export type ReviewStatus = 'unreviewed' | 'accepted' | 'rejected' | 'skipped';

export type RejectionReason =
  | 'transcript_incorrect'
  | 'multiple_speakers'
  | 'background_noise'
  | 'music'
  | 'clipping'
  | 'language_mismatch'
  | 'low_audio_quality'
  | 'too_short'
  | 'other';

export type ErrorCategory =
  | 'spelling'
  | 'pronunciation'
  | 'missing_word'
  | 'extra_word'
  | 'hallucination'
  | 'proper_noun'
  | 'english_word'
  | 'code_mix'
  | 'punctuation'
  | 'speaker_overlap'
  | 'background_noise'
  | 'music'
  | 'clipping'
  | 'other';

// ============================================================
// ASR error pair
// ============================================================
export interface AsrError {
  id: string;
  asr: string;
  correct: string;
}

// ============================================================
// Full review annotation for a segment
// ============================================================
export interface ReviewAnnotation {
  segment_id: string; // video_id + start as unique key
  original_transcript: string;
  corrected_transcript: string;
  review_status: ReviewStatus;
  rejection_reason?: RejectionReason;
  transcript_score?: number; // 1-5
  audio_quality_score?: number; // 1-5
  wrong_words: AsrError[];
  error_categories: ErrorCategory[];
  notes: string;
  reviewed_at?: string;
  reviewed_duration_ms?: number; // time spent on this sample
}

// ============================================================
// Combined segment with annotation
// ============================================================
export interface ReviewItem {
  id: string;
  index: number;
  segment: PipelineSegment;
  annotation: ReviewAnnotation;
}

// ============================================================
// Filter state
// ============================================================
export type FilterStatus = 'all' | ReviewStatus | 'corrected';
export type FilterLanguage = 'all' | string;
export type FilterEmotion = 'all' | string;
export type FilterChannel = 'all' | string;

export interface FilterState {
  status: FilterStatus;
  language: FilterLanguage;
  emotion: FilterEmotion;
  channel: FilterChannel;
  searchQuery: string;
  channelSearch: string;
}

// ============================================================
// Export formats
// ============================================================
export type ExportFormat = 'json' | 'csv';
export type ExportScope = 'all' | 'approved' | 'rejected' | 'reviewed' | 'filtered';

// ============================================================
// Analytics
// ============================================================
export interface AnalyticsData {
  total: number;
  reviewed: number;
  approved: number;
  rejected: number;
  skipped: number;
  remaining: number;
  approvalRate: number;
  avgTranscriptScore: number;
  avgAudioScore: number;
  correctionRate: number;
  rejectionReasonCounts: Record<string, number>;
  errorCategoryCounts: Record<string, number>;
  asrErrors: { asr: string; correct: string; count: number }[];
  languageDist: Record<string, number>;
  emotionDist: Record<string, number>;
  speakerDist: Record<string, number>;
  channelDist: Record<string, number>;
  durationBuckets: { range: string; count: number }[];
  dailyProgress: { date: string; reviewed: number; approved: number }[];
  totalAcceptedDuration: number; // seconds
  acceptedDurationPerLanguage: Record<string, number>; // lang -> seconds
}
