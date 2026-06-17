import React from 'react';
import { useReviewStore } from '../store/reviewStore';
import { clsx } from 'clsx';
import { CheckCircle2, XCircle, SkipForward } from 'lucide-react';
import type { ReviewStatus, RejectionReason } from '../types';

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

interface DecisionPanelProps {
  itemId: string;
  onDecision?: (status: ReviewStatus) => void;
}

export function DecisionPanel({ itemId, onDecision }: DecisionPanelProps) {
  const annotation = useReviewStore((s) => s.getAnnotation(itemId));
  const setStatus = useReviewStore((s) => s.setStatus);
  const setRejectionReason = useReviewStore((s) => s.setRejectionReason);

  if (!annotation) return null;

  const { review_status, rejection_reason } = annotation;

  const handleDecision = (status: ReviewStatus) => {
    setStatus(itemId, status);
    onDecision?.(status);
  };

  return (
    <div className="bg-surface-800/40 rounded-xl border border-surface-700/30 overflow-hidden">
      <div className="px-4 py-3 border-b border-surface-700/30">
        <h3 className="text-sm font-semibold text-surface-100">Dataset Decision</h3>
      </div>

      <div className="p-4">
        {/* Decision buttons */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <DecisionButton
            label="Accept"
            shortcut="A"
            icon={<CheckCircle2 size={20} />}
            active={review_status === 'accepted'}
            activeClass="bg-success-500/20 border-success-500/50 text-success-300 shadow-success-500/10"
            inactiveClass="bg-surface-800/60 border-surface-700/40 text-surface-400 hover:bg-success-500/10 hover:border-success-500/30 hover:text-success-300"
            onClick={() => handleDecision('accepted')}
          />
          <DecisionButton
            label="Reject"
            shortcut="R"
            icon={<XCircle size={20} />}
            active={review_status === 'rejected'}
            activeClass="bg-danger-500/20 border-danger-500/50 text-danger-300 shadow-danger-500/10"
            inactiveClass="bg-surface-800/60 border-surface-700/40 text-surface-400 hover:bg-danger-500/10 hover:border-danger-500/30 hover:text-danger-300"
            onClick={() => handleDecision('rejected')}
          />
          <DecisionButton
            label="Skip"
            shortcut="S"
            icon={<SkipForward size={20} />}
            active={review_status === 'skipped'}
            activeClass="bg-warning-500/20 border-warning-500/50 text-warning-300 shadow-warning-500/10"
            inactiveClass="bg-surface-800/60 border-surface-700/40 text-surface-400 hover:bg-warning-500/10 hover:border-warning-500/30 hover:text-warning-300"
            onClick={() => handleDecision('skipped')}
          />
        </div>

        {/* Rejection reasons */}
        {review_status === 'rejected' && (
          <div className="animate-fade-in">
            <p className="text-[11px] text-surface-400 mb-2 font-medium">Rejection reason</p>
            <div className="flex flex-wrap gap-1.5">
              {REJECTION_REASONS.map((r) => (
                <button
                  key={r.value}
                  onClick={() =>
                    setRejectionReason(itemId, rejection_reason === r.value ? undefined : r.value)
                  }
                  className={clsx(
                    'px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-all',
                    rejection_reason === r.value
                      ? 'bg-danger-500/20 border-danger-500/40 text-danger-300'
                      : 'bg-surface-800/60 border-surface-700/30 text-surface-400 hover:border-surface-600/50 hover:text-surface-200'
                  )}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Status display */}
        {review_status !== 'unreviewed' && (
          <div className="mt-3 pt-3 border-t border-surface-700/30">
            <StatusBadge status={review_status} />
          </div>
        )}
      </div>
    </div>
  );
}

interface DecisionButtonProps {
  label: string;
  shortcut: string;
  icon: React.ReactNode;
  active: boolean;
  activeClass: string;
  inactiveClass: string;
  onClick: () => void;
}

function DecisionButton({ label, shortcut, icon, active, activeClass, inactiveClass, onClick }: DecisionButtonProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex flex-col items-center gap-2 py-4 rounded-xl border font-semibold text-sm transition-all duration-150',
        'shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-surface-900',
        active ? `${activeClass} shadow-md` : inactiveClass
      )}
    >
      {icon}
      <span>{label}</span>
      <kbd className="text-[9px] bg-black/20 px-1.5 py-0.5 rounded font-mono opacity-70">{shortcut}</kbd>
    </button>
  );
}

function StatusBadge({ status }: { status: ReviewStatus }) {
  const configs = {
    accepted: { label: 'Accepted ✓', cls: 'bg-success-500/10 text-success-300 border-success-500/20' },
    rejected: { label: 'Rejected ✗', cls: 'bg-danger-500/10 text-danger-300 border-danger-500/20' },
    skipped: { label: 'Skipped →', cls: 'bg-warning-500/10 text-warning-300 border-warning-500/20' },
    unreviewed: { label: 'Unreviewed', cls: 'bg-surface-700/30 text-surface-400 border-surface-700/30' },
  };
  const config = configs[status];
  return (
    <span className={clsx('text-[11px] px-3 py-1 rounded-full border font-medium', config.cls)}>
      {config.label}
    </span>
  );
}
