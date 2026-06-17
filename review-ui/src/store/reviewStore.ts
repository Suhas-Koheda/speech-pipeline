import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  ReviewItem,
  ReviewAnnotation,
  PipelineSegment,
  FilterState,
  ReviewStatus,
  RejectionReason,
  ErrorCategory,
  AsrError,
} from '../types';

// ─── helpers ────────────────────────────────────────────────────────────────

export function makeSegmentId(seg: PipelineSegment): string {
  return `${seg.video_id}__${seg.start.toFixed(3)}`;
}

function defaultAnnotation(seg: PipelineSegment): ReviewAnnotation {
  return {
    segment_id: makeSegmentId(seg),
    original_transcript: seg.transcript,
    corrected_transcript: seg.transcript,
    review_status: 'unreviewed',
    wrong_words: [],
    error_categories: [],
    notes: '',
  };
}

function buildItems(segments: PipelineSegment[]): ReviewItem[] {
  return segments.map((seg, index) => ({
    id: makeSegmentId(seg),
    index,
    segment: seg,
    annotation: defaultAnnotation(seg),
  }));
}

// ─── store interface ─────────────────────────────────────────────────────────

interface ReviewStore {
  // Data
  items: ReviewItem[];
  annotations: Record<string, ReviewAnnotation>; // id -> annotation
  currentIndex: number;

  // Filter
  filters: FilterState;

  // UI
  isLoaded: boolean;
  datasetName: string;
  preferredPlaybackRate: number;

  // Actions - data
  loadSegments: (segments: PipelineSegment[], name?: string) => void;
  importAnnotations: (annotations: ReviewAnnotation[], merge?: boolean) => void;

  // Actions - navigation
  setCurrentIndex: (index: number) => void;
  goNext: () => void;
  goPrev: () => void;

  // Actions - annotation
  updateAnnotation: (id: string, patch: Partial<ReviewAnnotation>) => void;
  setStatus: (id: string, status: ReviewStatus) => void;
  setTranscriptScore: (id: string, score: number) => void;
  setAudioScore: (id: string, score: number) => void;
  setRejectionReason: (id: string, reason: RejectionReason | undefined) => void;
  setCorrectedTranscript: (id: string, text: string) => void;
  setErrorCategories: (id: string, cats: ErrorCategory[]) => void;
  addWrongWord: (id: string, entry: AsrError) => void;
  removeWrongWord: (id: string, entryId: string) => void;
  updateWrongWord: (id: string, entry: AsrError) => void;
  setNotes: (id: string, notes: string) => void;

  // Actions - filter
  setFilter: (patch: Partial<FilterState>) => void;
  clearFilters: () => void;
  setPreferredPlaybackRate: (rate: number) => void;

  // Computed
  getFilteredItems: () => ReviewItem[];
  getItem: (id: string) => ReviewItem | undefined;
  getAnnotation: (id: string) => ReviewAnnotation | undefined;
  getCurrentItem: () => ReviewItem | undefined;
  getStats: () => {
    total: number;
    reviewed: number;
    approved: number;
    rejected: number;
    skipped: number;
    unreviewed: number;
    corrected: number;
    approvalRate: number;
  };
}

// ─── default filters ─────────────────────────────────────────────────────────

const defaultFilters: FilterState = {
  status: 'all',
  language: 'all',
  emotion: 'all',
  channel: 'all',
  searchQuery: '',
  channelSearch: '',
};

// ─── store ───────────────────────────────────────────────────────────────────

export const useReviewStore = create<ReviewStore>()(
  persist(
    (set, get) => ({
      items: [],
      annotations: {},
      currentIndex: 0,
      filters: defaultFilters,
      isLoaded: false,
      datasetName: '',
      preferredPlaybackRate: 1.0,

      // ── data loading ──────────────────────────────────────────────────────

      loadSegments: (segments, name = 'dataset') => {
        const newItems = buildItems(segments);
        const newAnnotations: Record<string, ReviewAnnotation> = {};
        const existing = get().annotations;

        for (const item of newItems) {
          // Preserve existing annotations on re-import
          newAnnotations[item.id] = existing[item.id] ?? item.annotation;
        }

        // Sync items' annotation references
        const hydratedItems = newItems.map((item) => ({
          ...item,
          annotation: newAnnotations[item.id],
        }));

        set({ items: hydratedItems, annotations: newAnnotations, isLoaded: true, datasetName: name });
      },

      importAnnotations: (incomingAnnotations, merge = true) => {
        const existing = get().annotations;
        const updated = { ...existing };

        for (const ann of incomingAnnotations) {
          if (merge && existing[ann.segment_id]?.review_status !== 'unreviewed') {
            // Don't overwrite existing reviewed items unless new one is reviewed too
            if (ann.review_status === 'unreviewed') continue;
          }
          updated[ann.segment_id] = ann;
        }

        // Find first unreviewed to resume from
        const items = get().items;
        let resumeIndex = 0;
        for (let i = 0; i < items.length; i++) {
          if (updated[items[i].id]?.review_status !== 'unreviewed') {
            resumeIndex = i + 1;
          }
        }

        set({
          annotations: updated,
          items: items.map((item) => ({ ...item, annotation: updated[item.id] ?? item.annotation })),
          currentIndex: Math.min(resumeIndex, items.length - 1),
        });
      },

      // ── navigation ────────────────────────────────────────────────────────

      setCurrentIndex: (index) => {
        const len = get().items.length;
        if (len === 0) return;
        set({ currentIndex: Math.max(0, Math.min(index, len - 1)) });
      },

      goNext: () => {
        const { currentIndex, items } = get();
        if (currentIndex < items.length - 1) {
          set({ currentIndex: currentIndex + 1 });
        }
      },

      goPrev: () => {
        const { currentIndex } = get();
        if (currentIndex > 0) {
          set({ currentIndex: currentIndex - 1 });
        }
      },

      // ── annotation helpers ────────────────────────────────────────────────

      updateAnnotation: (id, patch) => {
        const existing = get().annotations[id];
        if (!existing) return;
        const updated = { ...existing, ...patch, reviewed_at: new Date().toISOString() };
        set((state) => ({
          annotations: { ...state.annotations, [id]: updated },
          items: state.items.map((item) =>
            item.id === id ? { ...item, annotation: updated } : item
          ),
        }));
      },

      setStatus: (id, status) => {
        get().updateAnnotation(id, { review_status: status });
      },

      setTranscriptScore: (id, score) => {
        get().updateAnnotation(id, { transcript_score: score });
      },

      setAudioScore: (id, score) => {
        get().updateAnnotation(id, { audio_quality_score: score });
      },

      setRejectionReason: (id, reason) => {
        get().updateAnnotation(id, { rejection_reason: reason });
      },

      setCorrectedTranscript: (id, text) => {
        get().updateAnnotation(id, { corrected_transcript: text });
      },

      setErrorCategories: (id, cats) => {
        get().updateAnnotation(id, { error_categories: cats });
      },

      addWrongWord: (id, entry) => {
        const ann = get().annotations[id];
        if (!ann) return;
        get().updateAnnotation(id, { wrong_words: [...ann.wrong_words, entry] });
      },

      removeWrongWord: (id, entryId) => {
        const ann = get().annotations[id];
        if (!ann) return;
        get().updateAnnotation(id, { wrong_words: ann.wrong_words.filter((w) => w.id !== entryId) });
      },

      updateWrongWord: (id, entry) => {
        const ann = get().annotations[id];
        if (!ann) return;
        get().updateAnnotation(id, {
          wrong_words: ann.wrong_words.map((w) => (w.id === entry.id ? entry : w)),
        });
      },

      setNotes: (id, notes) => {
        get().updateAnnotation(id, { notes });
      },

      // ── filters ───────────────────────────────────────────────────────────

      setFilter: (patch) => {
        set((state) => ({ filters: { ...state.filters, ...patch } }));
      },

      clearFilters: () => {
        set({ filters: defaultFilters });
      },

      setPreferredPlaybackRate: (rate) => {
        set({ preferredPlaybackRate: rate });
      },

      // ── computed ──────────────────────────────────────────────────────────

      getFilteredItems: () => {
        const { items, filters } = get();
        return items.filter((item) => {
          const ann = item.annotation;
          const seg = item.segment;

          // Status filter
          if (filters.status !== 'all') {
            if (filters.status === 'corrected') {
              if (ann.corrected_transcript === ann.original_transcript) return false;
            } else if (ann.review_status !== filters.status) {
              return false;
            }
          }

          // Language filter
          if (filters.language !== 'all' && seg.language !== filters.language) return false;

          // Emotion filter
          if (filters.emotion !== 'all' && seg.emotion !== filters.emotion) return false;

          // Channel filter
          if (filters.channel !== 'all' && seg.channel !== filters.channel) return false;

          // Search
          if (filters.searchQuery) {
            const q = filters.searchQuery.toLowerCase();
            const haystack = `${seg.transcript} ${ann.corrected_transcript}`.toLowerCase();
            if (!haystack.includes(q)) return false;
          }

          if (filters.channelSearch) {
            const q = filters.channelSearch.toLowerCase();
            if (!seg.channel.toLowerCase().includes(q)) return false;
          }

          return true;
        });
      },

      getItem: (id) => get().items.find((i) => i.id === id),

      getAnnotation: (id) => get().annotations[id],

      getCurrentItem: () => {
        const { items, currentIndex } = get();
        return items[currentIndex];
      },

      getStats: () => {
        const { items } = get();
        const total = items.length;
        const approved = items.filter((i) => i.annotation.review_status === 'accepted').length;
        const rejected = items.filter((i) => i.annotation.review_status === 'rejected').length;
        const skipped = items.filter((i) => i.annotation.review_status === 'skipped').length;
        const unreviewed = items.filter((i) => i.annotation.review_status === 'unreviewed').length;
        const reviewed = total - unreviewed;
        const corrected = items.filter(
          (i) => i.annotation.corrected_transcript !== i.annotation.original_transcript
        ).length;
        const approvalRate = reviewed > 0 ? (approved / reviewed) * 100 : 0;

        return { total, reviewed, approved, rejected, skipped, unreviewed, corrected, approvalRate };
      },
    }),
    {
      name: 'speech-review-store-v1',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        items: state.items,
        annotations: state.annotations,
        currentIndex: state.currentIndex,
        isLoaded: state.isLoaded,
        datasetName: state.datasetName,
        filters: state.filters,
        preferredPlaybackRate: state.preferredPlaybackRate,
      }),
    }
  )
);
