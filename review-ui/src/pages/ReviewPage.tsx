import React from 'react';
import { Sidebar } from '../components/Sidebar';
import { ReviewPanel } from '../components/ReviewPanel';
import { useReviewStore } from '../store/reviewStore';
import { Link } from 'react-router-dom';
import { BarChart2, Database, Save, Tag } from 'lucide-react';

export function ReviewPage() {
  const isLoaded = useReviewStore((s) => s.isLoaded);
  const datasetName = useReviewStore((s) => s.datasetName);
  const triageCount = useReviewStore((s) =>
    s.items.filter((i) => i.annotation.review_status === 'rejected' || i.annotation.review_status === 'skipped').length
  );

  return (
    <div className="flex flex-col h-screen bg-surface-950 text-surface-100 overflow-hidden">
      {/* Global top bar */}
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-surface-700/40 bg-surface-900/80 backdrop-blur-sm shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center">
            <span className="text-white text-[10px] font-bold">SR</span>
          </div>
          <h1 className="text-sm font-bold text-surface-100">
            Speech Review
            {datasetName && (
              <span className="ml-2 text-xs font-normal text-surface-400">— {datasetName}</span>
            )}
          </h1>
        </div>

        <nav className="flex items-center gap-1">
          <NavLink to="/" icon={<Save size={13} />} label="Review" active />
          <NavLink to="/triage" icon={<Tag size={13} />} label="Triage" badge={triageCount} />
          <NavLink to="/analytics" icon={<BarChart2 size={13} />} label="Analytics" />
          <NavLink to="/data" icon={<Database size={13} />} label="Dataset" />
        </nav>

        <div className="flex items-center gap-2 text-[10px] text-surface-500">
          <div className="w-1.5 h-1.5 rounded-full bg-success-400 animate-pulse" />
          Autosaved
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {isLoaded ? (
          <>
            <Sidebar />
            <ReviewPanel />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4 max-w-sm">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-500/20 to-accent-700/10 flex items-center justify-center mx-auto border border-accent-500/20">
                <Database size={28} className="text-accent-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-surface-100">No Dataset Loaded</h2>
                <p className="text-sm text-surface-400 mt-1">
                  Import a <code className="text-accent-300 text-xs">.jsonl</code> file to start reviewing.
                </p>
              </div>
              <Link
                to="/data"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent-500 hover:bg-accent-400 text-white text-sm font-semibold rounded-xl transition-colors"
              >
                <Database size={15} />
                Import Dataset
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function NavLink({
  to,
  icon,
  label,
  active,
  badge,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  badge?: number;
}) {
  return (
    <Link
      to={to}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
        active
          ? 'bg-accent-500/15 text-accent-300'
          : 'text-surface-400 hover:text-surface-200 hover:bg-surface-800/60'
      }`}
    >
      {icon}
      {label}
      {badge != null && badge > 0 && (
        <span className="ml-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-warning-500/20 text-warning-300">
          {badge}
        </span>
      )}
    </Link>
  );
}
