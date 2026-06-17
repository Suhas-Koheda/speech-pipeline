import { useEffect, useCallback } from 'react';
import { useReviewStore } from '../store/reviewStore';

interface ShortcutOptions {
  onAccept?: () => void;
  onReject?: () => void;
  onSkip?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  onPlayPause?: () => void;
  onFocusTranscript?: () => void;
  onFocusNotes?: () => void;
  onExport?: () => void;
  onHelp?: () => void;
}

export function useKeyboardShortcuts(opts: ShortcutOptions) {
  const { getCurrentItem, setTranscriptScore, setAudioScore } = useReviewStore();

  const handler = useCallback(
    (e: KeyboardEvent) => {
      const active = document.activeElement;
      const isInput =
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active as HTMLElement)?.isContentEditable;

      // These shortcuts work even in inputs
      if (e.key === 'Escape') {
        (active as HTMLElement)?.blur();
        return;
      }

      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        opts.onExport?.();
        return;
      }

      // Skip if typing in an input (except global shortcuts)
      if (isInput) return;

      const item = getCurrentItem();
      const id = item?.id;

      switch (e.key) {
        case ' ':
          e.preventDefault();
          opts.onPlayPause?.();
          break;
        case 'a':
        case 'A':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            opts.onAccept?.();
          }
          break;
        case 'r':
        case 'R':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            opts.onReject?.();
          }
          break;
        case 's':
        case 'S':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            opts.onSkip?.();
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          opts.onNext?.();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          opts.onPrev?.();
          break;
        case 't':
        case 'T':
          e.preventDefault();
          opts.onFocusTranscript?.();
          break;
        case 'n':
        case 'N':
          e.preventDefault();
          opts.onFocusNotes?.();
          break;
        case '?':
          e.preventDefault();
          opts.onHelp?.();
          break;
        case '1':
        case '2':
        case '3':
        case '4':
        case '5': {
          if (!id) break;
          const score = parseInt(e.key);
          if (e.shiftKey) {
            setAudioScore(id, score);
          } else {
            setTranscriptScore(id, score);
          }
          break;
        }
      }
    },
    [opts, getCurrentItem, setTranscriptScore, setAudioScore]
  );

  useEffect(() => {
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handler]);
}
