import { useCallback, useRef, useState } from 'react';
import { useReviewStore } from '../store/reviewStore';
import { AudioPlayer } from './AudioPlayer';
import { TranscriptReview } from './TranscriptReview';
import { DecisionPanel } from './DecisionPanel';
import { AsrErrorAnalysis } from './AsrErrorAnalysis';
import { NotesField } from './NotesField';
import { ShortcutHelp } from './ShortcutHelp';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { exportData } from '../utils/dataUtils';
import {
  ChevronLeft,
  ChevronRight,
  Keyboard,
  Download,
} from 'lucide-react';
import type { ReviewStatus } from '../types';

export function ReviewPanel() {
  const {
    currentIndex,
    items,
    getCurrentItem,
    goNext,
    goPrev,
    setStatus,
    getStats,
    autoplayEnabled,
    setAutoplayEnabled,
  } = useReviewStore();

  const [showHelp, setShowHelp] = useState(false);

  const currentItem = getCurrentItem();
  const stats = getStats();

  const playerRef = useRef<{ togglePlay: () => void } | null>(null);
  const transcriptRef = useRef<HTMLTextAreaElement>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);


  const handleDecision = useCallback(
    (status: ReviewStatus) => {
      if (status !== 'skipped') goNext();
    },
    [goNext]
  );

  const handleAccept = useCallback(() => {
    if (currentItem) {
      setStatus(currentItem.id, 'accepted');
      goNext();
    }
  }, [currentItem, setStatus, goNext]);

  const handleReject = useCallback(() => {
    if (currentItem) {
      setStatus(currentItem.id, 'rejected');
      goNext();
    }
  }, [currentItem, setStatus, goNext]);

  const handleSkip = useCallback(() => {
    if (currentItem) {
      setStatus(currentItem.id, 'skipped');
      goNext();
    }
  }, [currentItem, setStatus, goNext]);

  const handleExport = useCallback(() => {
    exportData(items, 'json', 'all');
  }, [items]);

  useKeyboardShortcuts({
    onAccept: handleAccept,
    onReject: handleReject,
    onSkip: handleSkip,
    onNext: goNext,
    onPrev: goPrev,
    onPlayPause: () => playerRef.current?.togglePlay(),
    onFocusTranscript: () => transcriptRef.current?.focus(),
    onFocusNotes: () => notesRef.current?.focus(),
    onExport: handleExport,
    onHelp: () => setShowHelp((v) => !v),
  });

  if (!currentItem) {
    return (
      <div className="flex-1 flex items-center justify-center text-surface-500">
        <p>No samples loaded. Import a JSONL file to begin.</p>
      </div>
    );
  }

  return (
    <main className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-700/40 bg-surface-900/60 shrink-0">
        <div className="flex items-center gap-3">
          {/* Navigation */}
          <button
            onClick={goPrev}
            disabled={currentIndex === 0}
            className="p-1.5 rounded-lg bg-surface-800/60 text-surface-400 hover:text-surface-200 hover:bg-surface-700/60 disabled:opacity-30 transition-all"
            title="Previous (←)"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-xs font-mono text-surface-400">
            <span className="text-surface-200 font-semibold">{currentIndex + 1}</span>
            <span className="mx-1">/</span>
            {stats.total}
          </span>
          <button
            onClick={goNext}
            disabled={currentIndex === items.length - 1}
            className="p-1.5 rounded-lg bg-surface-800/60 text-surface-400 hover:text-surface-200 hover:bg-surface-700/60 disabled:opacity-30 transition-all"
            title="Next (→)"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-surface-400 hover:text-surface-200 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoplayEnabled}
              onChange={(e) => setAutoplayEnabled(e.target.checked)}
              className="rounded border-surface-700 bg-surface-800 text-accent-500 focus:ring-accent-500/30 focus:ring-offset-0 cursor-pointer"
            />
            Autoplay next segment
          </label>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-800/60 text-surface-300 hover:text-surface-100 hover:bg-surface-700/60 text-xs transition-all border border-surface-700/30"
              title="Export (Ctrl+S)"
            >
              <Download size={13} />
              Export
            </button>
            <button
              onClick={() => setShowHelp(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-800/60 text-surface-300 hover:text-surface-100 hover:bg-surface-700/60 text-xs transition-all border border-surface-700/30"
              title="Shortcuts (?)"
            >
              <Keyboard size={13} />
              Shortcuts
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {/* Audio player */}
        <AudioPlayer
          item={currentItem}
          autoPlay={autoplayEnabled}
          playerRef={playerRef}
        />

        {/* Transcript */}
        <TranscriptReview
          key={`tx-${currentItem.id}`}
          itemId={currentItem.id}
          transcriptRef={transcriptRef}
        />

        {/* Decision */}
        <DecisionPanel
          key={`d-${currentItem.id}`}
          itemId={currentItem.id}
          onDecision={handleDecision}
        />

        {/* ASR errors */}
        <AsrErrorAnalysis key={`asr-${currentItem.id}`} itemId={currentItem.id} />

        {/* Notes */}
        <NotesField
          key={`n-${currentItem.id}`}
          itemId={currentItem.id}
          notesRef={notesRef}
        />
      </div>

      {showHelp && <ShortcutHelp onClose={() => setShowHelp(false)} />}
    </main>
  );
}
