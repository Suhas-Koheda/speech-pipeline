import React from 'react';
import { ImportExportPanel } from '../components/ImportExportPanel';
import { Link } from 'react-router-dom';
import { BarChart2, Save, Database, Tag } from 'lucide-react';

export function DataPage() {
  return (
    <div className="flex flex-col h-screen bg-surface-950 text-surface-100 overflow-hidden">
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-surface-700/40 bg-surface-900/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center">
            <span className="text-white text-[10px] font-bold">SR</span>
          </div>
          <h1 className="text-sm font-bold text-surface-100">Speech Review</h1>
        </div>
        <nav className="flex items-center gap-1">
          <NavLink to="/" icon={<Save size={13} />} label="Review" />
          <NavLink to="/triage" icon={<Tag size={13} />} label="Triage" />
          <NavLink to="/analytics" icon={<BarChart2 size={13} />} label="Analytics" />
          <NavLink to="/data" icon={<Database size={13} />} label="Dataset" active />
        </nav>
        <div className="w-24" />
      </header>
      <div className="flex-1 overflow-auto">
        <ImportExportPanel />
      </div>
    </div>
  );
}

function NavLink({
  to,
  icon,
  label,
  active,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  active?: boolean;
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
    </Link>
  );
}
