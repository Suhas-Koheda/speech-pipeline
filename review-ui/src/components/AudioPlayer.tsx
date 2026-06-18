import React, { useRef, useCallback } from 'react';
import { useWaveSurfer } from '../hooks/useWaveSurfer';
import { useReviewStore } from '../store/reviewStore';
import { clsx } from 'clsx';
import {
  Play,
  Pause,
  RotateCcw,
  Clock,
  User,
  Mic,
  Globe,
  LayoutGrid,
  AlertCircle,
} from 'lucide-react';
import type { ReviewItem } from '../types';

const SPEEDS = [0.75, 1.0, 1.25, 1.5, 2.0];

// Normalize segment paths like ../segments/... → /segments/... for the Vite proxy
function resolveAudioPath(raw: string): string {
  if (!raw) return '';
  if (raw.startsWith('http') || raw.startsWith('blob:')) return raw;
  const clean = raw.replace(/^(\.\.\/)+/, '/').replace(/^\.\//, '/');
  return clean.startsWith('/') ? clean : `/${clean}`;
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  const ms = Math.floor((s % 1) * 10);
  return `${m}:${String(sec).padStart(2, '0')}.${ms}`;
}

interface AudioPlayerProps {
  item: ReviewItem;
  autoPlay?: boolean;
  onPlayPause?: (isPlaying: boolean) => void;
  playerRef?: React.MutableRefObject<{ togglePlay: () => void } | null>;
}

export function AudioPlayer({ item, autoPlay = false, onPlayPause, playerRef }: AudioPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Global persisted rate
  const preferredRate = useReviewStore((s) => s.preferredPlaybackRate);
  const setPreferredPlaybackRate = useReviewStore((s) => s.setPreferredPlaybackRate);

  const audioPath = resolveAudioPath(item.segment.segment_path || item.segment.audio_path || '');

  const { isPlaying, isReady, currentTime, duration, playbackRate, error, togglePlay, setPlaybackRate, replay } =
    useWaveSurfer(containerRef as React.RefObject<HTMLDivElement>, {
      audioPath,
      segmentIdentifier: item.segment.title || item.id,
      initialRate: preferredRate,
      autoPlay,
    });

  // Expose togglePlay to parent
  React.useEffect(() => {
    if (playerRef) {
      playerRef.current = { togglePlay };
    }
  }, [playerRef, togglePlay]);

  React.useEffect(() => {
    onPlayPause?.(isPlaying);
  }, [isPlaying, onPlayPause]);

  // When user changes speed, persist it globally
  const handleSetRate = useCallback(
    (rate: number) => {
      setPlaybackRate(rate);
      setPreferredPlaybackRate(rate);
    },
    [setPlaybackRate, setPreferredPlaybackRate]
  );

  return (
    <div className="bg-surface-800/40 backdrop-blur-sm rounded-xl border border-surface-700/30 overflow-hidden">
      {/* Metadata bar */}
      <div className="px-4 pt-4 pb-3 border-b border-surface-700/30">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-surface-100 truncate">{item.segment.title}</h3>
            <p className="text-xs text-surface-400 truncate">{item.segment.channel}</p>
          </div>
          <div className="text-right shrink-0">
            <span className="text-xs font-mono text-accent-400">
              #{String(item.index + 1).padStart(4, '0')}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
          <MetaBadge icon={<Clock size={11} />} label={`${item.segment.duration.toFixed(2)}s`} />
          <MetaBadge icon={<Globe size={11} />} label={item.segment.language} />
          <MetaBadge
            icon={<User size={11} />}
            label={item.segment.dominant_speaker ?? item.segment.speaker ?? 'unknown'}
          />
          {item.segment.emotion && (
            <MetaBadge icon={<Mic size={11} />} label={item.segment.emotion} />
          )}
          {item.segment.style && item.segment.style !== item.segment.emotion && (
            <MetaBadge icon={<LayoutGrid size={11} />} label={item.segment.style} />
          )}
        </div>
      </div>

      {/* Waveform */}
      <div className="px-4 pt-4">
        {error ? (
          <div className="flex items-center gap-2 h-20 bg-surface-900/60 rounded-lg justify-center text-danger-400 text-xs">
            <AlertCircle size={14} />
            <span>Audio unavailable: {error}</span>
          </div>
        ) : (
          <div className="relative">
            <div
              ref={containerRef}
              className={clsx(
                'rounded-lg overflow-hidden transition-opacity',
                isReady ? 'opacity-100' : 'opacity-40'
              )}
            />
            {!isReady && !error && (
              <div className="absolute inset-0 flex items-center justify-center h-20">
                <div className="flex gap-1 items-end">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="w-1 bg-accent-500/60 rounded-full animate-bounce"
                      style={{ height: `${16 + i * 8}px`, animationDelay: `${i * 0.1}s` }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Time display */}
        <div className="flex justify-between text-[10px] font-mono text-surface-500 mt-1 mb-3">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="px-4 pb-4 flex items-center gap-3">
        {/* Replay */}
        <button
          onClick={replay}
          disabled={!isReady}
          className="p-2 rounded-lg bg-surface-700/50 text-surface-300 hover:bg-surface-600/60 hover:text-surface-100 disabled:opacity-40 transition-all"
          title="Replay from start"
        >
          <RotateCcw size={16} />
        </button>

        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          disabled={!isReady}
          className={clsx(
            'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm transition-all',
            isPlaying
              ? 'bg-accent-500/20 text-accent-300 border border-accent-500/30 hover:bg-accent-500/30'
              : 'bg-accent-500 text-white hover:bg-accent-400 shadow-lg shadow-accent-500/20',
            !isReady && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          <span>{isPlaying ? 'Pause' : 'Play'}</span>
          <kbd className="ml-1 text-[10px] opacity-60 bg-white/10 px-1.5 py-0.5 rounded">Space</kbd>
        </button>

        {/* Speed — shows active rate from global store */}
        <div className="flex gap-1">
          {SPEEDS.map((speed) => (
            <button
              key={speed}
              onClick={() => handleSetRate(speed)}
              className={clsx(
                'px-2 py-1.5 rounded text-[10px] font-mono transition-colors',
                playbackRate === speed
                  ? 'bg-accent-500 text-white'
                  : 'bg-surface-700/50 text-surface-400 hover:bg-surface-600/50 hover:text-surface-200'
              )}
            >
              {speed}×
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MetaBadge({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-1 text-[11px] text-surface-400">
      <span className="text-surface-500">{icon}</span>
      <span>{label}</span>
    </div>
  );
}
