import React, { useRef, useCallback, useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useReviewStore } from '../store/reviewStore';
import { clsx } from 'clsx';
import {
  CheckCircle2,
  XCircle,
  SkipForward,
  Circle,
  Search,
  Filter,
  X,
} from 'lucide-react';
import type { ReviewItem, FilterStatus } from '../types';

const STATUS_ICONS: Record<string, React.ReactNode> = {
  accepted: <CheckCircle2 size={14} className="text-success-400 shrink-0" />,
  rejected: <XCircle size={14} className="text-danger-400 shrink-0" />,
  skipped: <SkipForward size={14} className="text-warning-400 shrink-0" />,
  unreviewed: <Circle size={14} className="text-surface-500 shrink-0" />,
};

function formatDuration(s: number): string {
  return s < 60 ? `${s.toFixed(1)}s` : `${Math.floor(s / 60)}m${Math.round(s % 60)}s`;
}

// ─── Single virtualized row ───────────────────────────────────────────────────

interface SampleRowProps {
  item: ReviewItem;
  isActive: boolean;
  onClick: () => void;
}

const SampleRow = React.memo(function SampleRow({ item, isActive, onClick }: SampleRowProps) {
  const { segment, annotation } = item;
  const isCorrected = annotation.corrected_transcript !== annotation.original_transcript;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left px-3 py-2.5 rounded-lg border transition-all duration-150 group',
        'focus:outline-none focus:ring-1 focus:ring-accent-500',
        isActive
          ? 'bg-accent-500/10 border-accent-500/40 shadow-sm'
          : 'bg-surface-800/40 border-surface-700/30 hover:bg-surface-700/50 hover:border-surface-600/50'
      )}
    >
      <div className="flex items-start gap-2">
        {STATUS_ICONS[annotation.review_status]}
        <div className="flex-1 min-w-0">
          <p className="text-xs text-surface-200 leading-snug line-clamp-2 font-medium">
            {annotation.corrected_transcript || annotation.original_transcript}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-surface-500 font-mono">
              {formatDuration(segment.duration)}
            </span>
            <span className="text-[10px] text-surface-500 bg-surface-700/60 px-1.5 rounded">
              {segment.language}
            </span>
            {segment.emotion && (
              <span className="text-[10px] text-surface-500 italic truncate">
                {segment.emotion}
              </span>
            )}
            {isCorrected && (
              <span className="text-[10px] text-accent-400 ml-auto shrink-0">✎</span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
});

// ─── Filter pills ─────────────────────────────────────────────────────────────

const FILTER_STATUSES: { label: string; value: FilterStatus }[] = [
  { label: 'All', value: 'all' },
  { label: 'Unreviewed', value: 'unreviewed' },
  { label: 'Accepted', value: 'accepted' },
  { label: 'Rejected', value: 'rejected' },
  { label: 'Skipped', value: 'skipped' },
  { label: 'Corrected', value: 'corrected' },
];

// ─── Sidebar component ────────────────────────────────────────────────────────

export function Sidebar() {
  const {
    items,
    currentIndex,
    filters,
    setCurrentIndex,
    setFilter,
    clearFilters,
    getFilteredItems,
    getStats,
  } = useReviewStore();

  const stats = getStats();
  const filteredItems = getFilteredItems();

  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: filteredItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 74,
    overscan: 10,
  });

  // Unique values for filter dropdowns
  const languages = useMemo(
    () => ['all', ...Array.from(new Set(items.map((i) => i.segment.language))).sort()],
    [items]
  );
  const emotions = useMemo(
    () => ['all', ...Array.from(new Set(items.map((i) => i.segment.emotion ?? '').filter(Boolean))).sort()],
    [items]
  );
  const channels = useMemo(
    () => ['all', ...Array.from(new Set(items.map((i) => i.segment.channel))).sort()],
    [items]
  );

  const handleItemClick = useCallback(
    (item: ReviewItem) => {
      const globalIndex = items.findIndex((i) => i.id === item.id);
      if (globalIndex >= 0) setCurrentIndex(globalIndex);
    },
    [items, setCurrentIndex]
  );

  const progressPct = stats.total > 0 ? (stats.reviewed / stats.total) * 100 : 0;

  return (
    <aside className="flex flex-col h-full bg-surface-900/80 backdrop-blur-sm border-r border-surface-700/40 w-72 shrink-0">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-surface-700/40">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-surface-100">Dataset</h2>
          <span className="text-xs text-surface-400 font-mono">
            {currentIndex + 1}/{stats.total}
          </span>
        </div>

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex justify-between text-[10px] text-surface-400 mb-1">
            <span>{stats.reviewed} reviewed</span>
            <span>{progressPct.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent-500 to-accent-400 rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Stat pills */}
        <div className="grid grid-cols-3 gap-1.5 text-[10px]">
          <Stat label="Accept" value={stats.approved} color="text-success-400" />
          <Stat label="Reject" value={stats.rejected} color="text-danger-400" />
          <Stat label="Skip" value={stats.skipped} color="text-warning-400" />
        </div>
        {stats.reviewed > 0 && (
          <p className="text-[10px] text-surface-400 mt-1.5 text-center">
            Approval rate:{' '}
            <span className="text-success-400 font-medium">{stats.approvalRate.toFixed(1)}%</span>
          </p>
        )}
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b border-surface-700/40 space-y-1.5">
        <SearchInput
          placeholder="Search transcripts…"
          value={filters.searchQuery}
          onChange={(v) => setFilter({ searchQuery: v })}
        />
      </div>

      {/* Status filter pills */}
      <div className="px-3 py-2 border-b border-surface-700/40">
        <div className="flex flex-wrap gap-1">
          {FILTER_STATUSES.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter({ status: f.value })}
              className={clsx(
                'px-2 py-0.5 rounded text-[10px] font-medium transition-colors',
                filters.status === f.value
                  ? 'bg-accent-500 text-white'
                  : 'bg-surface-700/50 text-surface-300 hover:bg-surface-600/50'
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Attribute filters */}
      <div className="px-3 py-2 border-b border-surface-700/40 space-y-1.5">
        <FilterSelect
          label="Language"
          value={filters.language}
          options={languages}
          onChange={(v) => setFilter({ language: v })}
        />
        <FilterSelect
          label="Emotion"
          value={filters.emotion}
          options={emotions}
          onChange={(v) => setFilter({ emotion: v })}
        />
        <FilterSelect
          label="Channel"
          value={filters.channel}
          options={channels}
          onChange={(v) => setFilter({ channel: v })}
        />
        {(filters.language !== 'all' || filters.emotion !== 'all' || filters.channel !== 'all') && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 text-[10px] text-surface-400 hover:text-surface-200"
          >
            <X size={10} /> Clear filters
          </button>
        )}
      </div>

      {/* Filtered count */}
      <div className="px-3 py-1.5 border-b border-surface-700/40">
        <p className="text-[10px] text-surface-400">
          {filteredItems.length} of {stats.total} shown
        </p>
      </div>

      {/* Virtualized list */}
      <div ref={parentRef} className="flex-1 overflow-y-auto px-2 py-2">
        <div
          style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const item = filteredItems[virtualRow.index];
            const globalIndex = items.findIndex((i) => i.id === item.id);
            return (
              <div
                key={virtualRow.key}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                  paddingBottom: '4px',
                }}
              >
                <SampleRow
                  item={item}
                  isActive={globalIndex === currentIndex}
                  onClick={() => handleItemClick(item)}
                />
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-surface-800/60 rounded px-2 py-1.5 text-center">
      <div className={clsx('font-bold text-sm', color)}>{value}</div>
      <div className="text-surface-400">{label}</div>
    </div>
  );
}

function SearchInput({
  placeholder,
  value,
  onChange,
}: {
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative">
      <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-surface-500" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-surface-800/60 border border-surface-700/40 rounded text-xs text-surface-200 pl-6 pr-2 py-1.5 placeholder:text-surface-500 focus:outline-none focus:border-accent-500/50"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-surface-500 hover:text-surface-300"
        >
          <X size={10} />
        </button>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <Filter size={10} className="text-surface-500 shrink-0" />
      <label className="text-[10px] text-surface-400 w-12 shrink-0">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 bg-surface-800/60 border border-surface-700/40 rounded text-[10px] text-surface-200 px-1.5 py-1 focus:outline-none focus:border-accent-500/50"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt === 'all' ? `All ${label}s` : opt}
          </option>
        ))}
      </select>
    </div>
  );
}
