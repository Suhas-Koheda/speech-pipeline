import React, { useRef } from 'react';
import { useReviewStore } from '../store/reviewStore';
import { StickyNote } from 'lucide-react';

interface NotesFieldProps {
  itemId: string;
  notesRef?: React.RefObject<HTMLTextAreaElement | null>;
}

export function NotesField({ itemId, notesRef }: NotesFieldProps) {
  const annotation = useReviewStore((s) => s.getAnnotation(itemId));
  const setNotes = useReviewStore((s) => s.setNotes);
  const internalRef = useRef<HTMLTextAreaElement>(null);
  const ref = notesRef ?? internalRef;

  if (!annotation) return null;

  return (
    <div className="bg-surface-800/40 rounded-xl border border-surface-700/30 overflow-hidden">
      <div className="px-4 py-3 border-b border-surface-700/30 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-surface-100 flex items-center gap-2">
          <StickyNote size={14} className="text-surface-400" />
          Review Notes
        </h3>
        <kbd className="text-[10px] bg-surface-700/60 px-1.5 py-0.5 rounded text-surface-400">N</kbd>
      </div>
      <div className="p-4">
        <textarea
          ref={ref as React.RefObject<HTMLTextAreaElement>}
          value={annotation.notes}
          onChange={(e) => setNotes(itemId, e.target.value)}
          rows={3}
          placeholder="Optional notes about this sample…"
          className="w-full bg-surface-900/60 border border-surface-700/30 rounded-lg p-3 text-sm text-surface-200 resize-none focus:outline-none focus:border-accent-500/50 focus:ring-1 focus:ring-accent-500/20 transition-colors placeholder:text-surface-500"
        />
        <p className="text-[10px] text-surface-500 mt-1">Autosaved automatically</p>
      </div>
    </div>
  );
}
