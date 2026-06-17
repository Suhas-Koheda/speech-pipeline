import React from 'react';
import { useReviewStore } from '../store/reviewStore';
import { clsx } from 'clsx';
import { Mic2, Headphones } from 'lucide-react';

const SCORE_LABELS: Record<number, string> = {
  5: 'Perfect',
  4: 'Minor errors',
  3: 'Understandable',
  2: 'Major errors',
  1: 'Unusable',
};

const AUDIO_LABELS: Record<number, string> = {
  5: 'Studio quality',
  4: 'Clean',
  3: 'Acceptable',
  2: 'Noisy',
  1: 'Unusable',
};

interface RatingProps {
  label: string;
  icon: React.ReactNode;
  value?: number;
  labels: Record<number, string>;
  shortcutHint?: string;
  onChange: (score: number) => void;
}

function RatingRow({ label, icon, value, labels, shortcutHint, onChange }: RatingProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-surface-400">{icon}</span>
        <label className="text-xs font-medium text-surface-200">{label}</label>
        {shortcutHint && (
          <span className="text-[10px] text-surface-500 ml-auto">{shortcutHint}</span>
        )}
      </div>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((score) => (
          <button
            key={score}
            onClick={() => onChange(score)}
            title={labels[score]}
            className={clsx(
              'flex-1 py-2.5 rounded-lg border font-bold text-sm transition-all duration-150',
              value === score
                ? 'bg-accent-500/20 border-accent-500/50 text-accent-300 shadow-sm shadow-accent-500/10'
                : 'bg-surface-800/40 border-surface-700/30 text-surface-500 hover:bg-surface-700/50 hover:border-surface-600/40 hover:text-surface-300'
            )}
          >
            {score}
          </button>
        ))}
      </div>
      {value != null && (
        <p className="text-[10px] text-surface-400 mt-1">{labels[value]}</p>
      )}
    </div>
  );
}

interface QualityReviewProps {
  itemId: string;
}

export function QualityReview({ itemId }: QualityReviewProps) {
  const annotation = useReviewStore((s) => s.getAnnotation(itemId));
  const setTranscriptScore = useReviewStore((s) => s.setTranscriptScore);
  const setAudioScore = useReviewStore((s) => s.setAudioScore);

  if (!annotation) return null;

  return (
    <div className="bg-surface-800/40 rounded-xl border border-surface-700/30 overflow-hidden">
      <div className="px-4 py-3 border-b border-surface-700/30">
        <h3 className="text-sm font-semibold text-surface-100">Quality Review</h3>
      </div>
      <div className="p-4 space-y-5">
        <RatingRow
          label="Transcript Accuracy"
          icon={<Mic2 size={14} />}
          value={annotation.transcript_score}
          labels={SCORE_LABELS}
          shortcutHint="Keys 1-5"
          onChange={(s) => setTranscriptScore(itemId, s)}
        />
        <RatingRow
          label="Audio Quality"
          icon={<Headphones size={14} />}
          value={annotation.audio_quality_score}
          labels={AUDIO_LABELS}
          shortcutHint="Shift+1-5"
          onChange={(s) => setAudioScore(itemId, s)}
        />
      </div>
    </div>
  );
}
