import React, { useRef } from 'react';
import { useReviewStore } from '../store/reviewStore';
import { wordDiff } from '../utils/dataUtils';
import { clsx } from 'clsx';
import { Lock, PenLine, RotateCcw } from 'lucide-react';

interface TranscriptReviewProps {
  itemId: string;
  transcriptRef?: React.RefObject<HTMLTextAreaElement | null>;
}

export function TranscriptReview({ itemId, transcriptRef }: TranscriptReviewProps) {
  const annotation = useReviewStore((s) => s.getAnnotation(itemId));
  const setCorrectedTranscript = useReviewStore((s) => s.setCorrectedTranscript);

  const internalRef = useRef<HTMLTextAreaElement>(null);
  const ref = transcriptRef ?? internalRef;

  if (!annotation) return null;

  const { original_transcript, corrected_transcript } = annotation;
  const isModified = corrected_transcript !== original_transcript;
  const diff = isModified ? wordDiff(original_transcript, corrected_transcript) : null;

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setCorrectedTranscript(itemId, e.target.value);
  };

  const handleReset = () => {
    setCorrectedTranscript(itemId, original_transcript);
  };

  return (
    <div className="bg-surface-800/40 rounded-xl border border-surface-700/30 overflow-hidden">
      <div className="px-4 py-3 border-b border-surface-700/30 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-surface-100 flex items-center gap-2">
          <PenLine size={14} className="text-accent-400" />
          Transcript Review
        </h3>
        {isModified && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-500/20 text-accent-300 border border-accent-500/30 font-medium">
              ✎ Corrected
            </span>
            <button
              onClick={handleReset}
              className="text-[10px] text-surface-400 hover:text-surface-200 flex items-center gap-1"
            >
              <RotateCcw size={10} /> Reset
            </button>
          </div>
        )}
        {!isModified && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-700/40 text-surface-400">
            Unchanged
          </span>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Original transcript (read-only) */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Lock size={11} className="text-surface-500" />
            <label className="text-[11px] text-surface-400 font-medium">Original (ASR)</label>
          </div>
          <div className="bg-surface-900/60 rounded-lg p-3 text-sm text-surface-300 font-mono leading-relaxed select-none border border-surface-700/20">
            {original_transcript || <span className="italic text-surface-500">No transcript</span>}
          </div>
        </div>

        {/* Visual diff */}
        {diff && (
          <div>
            <label className="text-[11px] text-surface-400 font-medium mb-1.5 block">
              Diff view
            </label>
            <div className="bg-surface-900/60 rounded-lg p-3 text-sm font-mono leading-relaxed border border-surface-700/20 flex flex-wrap gap-x-1">
              {diff.map((token, i) => (
                <span
                  key={i}
                  className={clsx(
                    'rounded px-0.5',
                    token.type === 'insert' && 'bg-success-500/20 text-success-300',
                    token.type === 'delete' && 'bg-danger-500/20 text-danger-300 line-through',
                    token.type === 'equal' && 'text-surface-300'
                  )}
                >
                  {token.text}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Editable corrected transcript */}
        <div>
          <label className="text-[11px] text-surface-400 font-medium mb-1.5 flex items-center gap-1.5">
            <PenLine size={11} className="text-accent-400" />
            Corrected Transcript
            <kbd className="text-[9px] bg-surface-700/60 px-1 rounded ml-1">T</kbd>
          </label>
          <textarea
            ref={ref as React.RefObject<HTMLTextAreaElement>}
            value={corrected_transcript}
            onChange={handleChange}
            rows={3}
            className="w-full bg-surface-900/60 border border-surface-700/30 rounded-lg p-3 text-sm text-surface-100 font-mono leading-relaxed resize-none focus:outline-none focus:border-accent-500/50 focus:ring-1 focus:ring-accent-500/20 transition-colors placeholder:text-surface-500"
            placeholder="Edit transcript if needed…"
          />
        </div>
      </div>
    </div>
  );
}
