import { useState, useMemo } from 'react';
import { useReviewStore } from '../store/reviewStore';
import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  XCircle,
  SkipForward,
  Tag,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import type { RejectionReason } from '../types';

const REJECTION_REASONS: { value: RejectionReason; label: string }[] = [
  { value: 'transcript_incorrect', label: 'Transcript incorrect' },
  { value: 'multiple_speakers', label: 'Multiple speakers' },
  { value: 'background_noise', label: 'Background noise' },
  { value: 'music', label: 'Music' },
  { value: 'clipping', label: 'Clipping' },
  { value: 'language_mismatch', label: 'Language mismatch' },
  { value: 'low_audio_quality', label: 'Low audio quality' },
  { value: 'too_short', label: 'Too short' },
  { value: 'other', label: 'Other' },
];

type ViewMode = 'rejected' | 'skipped' | 'both';

export function TriagePage() {
  const { items, setRejectionReason, setStatus, setCurrentIndex } = useReviewStore();
  const [viewMode, setViewMode] = useState<ViewMode>('both');

  const triageItems = useMemo(() => {
    return items.filter((item) => {
      const s = item.annotation.review_status;
      if (viewMode === 'rejected') return s === 'rejected';
      if (viewMode === 'skipped') return s === 'skipped';
      return s === 'rejected' || s === 'skipped';
    });
  }, [items, viewMode]);

  const unreasonedRejections = triageItems.filter(
    (i) => i.annotation.review_status === 'rejected' && !i.annotation.rejection_reason
  ).length;

  return (
    <div className="flex flex-col h-screen bg-surface-950 text-surface-100 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-surface-700/40 bg-surface-900/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center">
            <span className="text-white text-[10px] font-bold">SR</span>
          </div>
          <h1 className="text-sm font-bold text-surface-100">Speech Review</h1>
        </div>
        <nav className="flex items-center gap-1">
          <NavLink to="/" label="Review" />
          <NavLink to="/triage" label="Triage" active />
          <NavLink to="/analytics" label="Analytics" />
          <NavLink to="/data" label="Dataset" />
        </nav>
        <div className="w-24" />
      </header>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-5xl mx-auto space-y-5">

          {/* Page header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-surface-50 flex items-center gap-2">
                <Tag size={18} className="text-warning-400" />
                Rejection &amp; Skip Triage
              </h2>
              <p className="text-surface-400 text-xs mt-0.5">
                Review all rejected / skipped samples and assign reasons before exporting.
              </p>
            </div>

            {unreasonedRejections > 0 && (
              <div className="flex items-center gap-2 px-3 py-2 bg-danger-500/10 border border-danger-500/20 rounded-lg text-xs text-danger-300">
                <AlertCircle size={13} />
                {unreasonedRejections} rejected sample{unreasonedRejections !== 1 ? 's' : ''} missing a reason
              </div>
            )}
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-1.5">
            {(['both', 'rejected', 'skipped'] as ViewMode[]).map((mode) => {
              const count = items.filter((i) => {
                const s = i.annotation.review_status;
                if (mode === 'rejected') return s === 'rejected';
                if (mode === 'skipped') return s === 'skipped';
                return s === 'rejected' || s === 'skipped';
              }).length;
              return (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                    viewMode === mode
                      ? 'bg-accent-500/20 text-accent-300 border border-accent-500/30'
                      : 'bg-surface-800/50 text-surface-400 hover:bg-surface-700/50 border border-surface-700/30'
                  )}
                >
                  {mode === 'rejected' && <XCircle size={12} className="text-danger-400" />}
                  {mode === 'skipped' && <SkipForward size={12} className="text-warning-400" />}
                  {mode === 'both' && <Tag size={12} />}
                  <span className="capitalize">{mode === 'both' ? 'All' : mode}</span>
                  <span className={clsx('px-1.5 py-0.5 rounded-full text-[10px] font-bold',
                    viewMode === mode ? 'bg-accent-500/30 text-accent-200' : 'bg-surface-700/60 text-surface-400'
                  )}>{count}</span>
                </button>
              );
            })}
          </div>

          {/* Table */}
          {triageItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-surface-500">
              <CheckCircle2 size={36} className="text-success-500/40 mb-3" />
              <p className="text-sm font-medium text-surface-300">No items to triage</p>
              <p className="text-xs mt-1">
                {viewMode === 'rejected' ? 'No rejected samples yet.' : viewMode === 'skipped' ? 'No skipped samples yet.' : 'Accept, reject, or skip samples to see them here.'}
              </p>
            </div>
          ) : (
            <div className="bg-surface-900/40 border border-surface-700/30 rounded-xl overflow-hidden">
              {/* Table header */}
              <div className="grid grid-cols-[28px_1fr_80px_90px_180px_100px] gap-3 px-4 py-2.5 border-b border-surface-700/30 text-[10px] font-semibold text-surface-400 uppercase tracking-wide">
                <span>#</span>
                <span>Transcript</span>
                <span>Duration</span>
                <span>Status</span>
                <span>Rejection Reason</span>
                <span>Actions</span>
              </div>

              {/* Rows */}
              <div className="divide-y divide-surface-700/20">
                {triageItems.map((item) => {
                  const ann = item.annotation;
                  const isRejected = ann.review_status === 'rejected';

                  return (
                    <div
                      key={item.id}
                      className="grid grid-cols-[28px_1fr_80px_90px_180px_100px] gap-3 px-4 py-3 items-center hover:bg-surface-800/30 transition-colors group"
                    >
                      {/* Index */}
                      <span className="text-[10px] font-mono text-surface-500">
                        {item.index + 1}
                      </span>

                      {/* Transcript */}
                      <div className="min-w-0">
                        <p className="text-xs text-surface-200 line-clamp-2 leading-snug">
                          {ann.corrected_transcript || ann.original_transcript}
                        </p>
                        <p className="text-[10px] text-surface-500 mt-0.5 truncate">
                          {item.segment.channel} · {item.segment.language}
                          {item.segment.emotion ? ` · ${item.segment.emotion}` : ''}
                        </p>
                      </div>

                      {/* Duration */}
                      <span className="text-[11px] font-mono text-surface-400">
                        {item.segment.duration.toFixed(1)}s
                      </span>

                      {/* Status badge */}
                      <div>
                        {isRejected ? (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-danger-500/10 text-danger-300 border border-danger-500/20 font-medium">
                            <XCircle size={9} /> Rejected
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-warning-500/10 text-warning-300 border border-warning-500/20 font-medium">
                            <SkipForward size={9} /> Skipped
                          </span>
                        )}
                      </div>

                      {/* Rejection reason dropdown */}
                      <div>
                        <select
                          value={ann.rejection_reason ?? ''}
                          onChange={(e) =>
                            setRejectionReason(
                              item.id,
                              (e.target.value as RejectionReason) || undefined
                            )
                          }
                          className={clsx(
                            'w-full bg-surface-800/60 border rounded px-2 py-1.5 text-[11px] focus:outline-none focus:border-accent-500/50 transition-colors',
                            !ann.rejection_reason && isRejected
                              ? 'border-danger-500/40 text-danger-400'
                              : 'border-surface-700/30 text-surface-300'
                          )}
                        >
                          <option value="">— pick reason —</option>
                          {REJECTION_REASONS.map((r) => (
                            <option key={r.value} value={r.value}>
                              {r.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1.5">
                        {/* Accept (un-reject) */}
                        <button
                          onClick={() => setStatus(item.id, 'accepted')}
                          title="Mark as accepted"
                          className="p-1.5 rounded-lg text-surface-500 hover:text-success-400 hover:bg-success-500/10 transition-colors"
                        >
                          <CheckCircle2 size={14} />
                        </button>

                        {/* Go to sample */}
                        <Link
                          to="/"
                          onClick={() => setCurrentIndex(item.index)}
                          title="Open in review"
                          className="p-1.5 rounded-lg text-surface-500 hover:text-accent-400 hover:bg-accent-500/10 transition-colors"
                        >
                          <ChevronRight size={14} />
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Footer summary */}
              <div className="px-4 py-2.5 border-t border-surface-700/30 bg-surface-900/40 flex items-center justify-between">
                <span className="text-[10px] text-surface-500">
                  {triageItems.length} sample{triageItems.length !== 1 ? 's' : ''} shown
                </span>
                {unreasonedRejections === 0 && triageItems.some(i => i.annotation.review_status === 'rejected') && (
                  <span className="text-[10px] text-success-400 flex items-center gap-1">
                    <CheckCircle2 size={10} /> All rejections have reasons
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function NavLink({ to, label, active }: { to: string; label: string; active?: boolean }) {
  return (
    <Link
      to={to}
      className={clsx(
        'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
        active
          ? 'bg-accent-500/15 text-accent-300'
          : 'text-surface-400 hover:text-surface-200 hover:bg-surface-800/60'
      )}
    >
      {label}
    </Link>
  );
}
