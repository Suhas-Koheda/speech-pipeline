import { X, Keyboard } from 'lucide-react';

interface ShortcutHelpProps {
  onClose: () => void;
}

const SHORTCUTS = [
  { key: 'Space', desc: 'Play / Pause audio' },
  { key: 'A', desc: 'Accept sample' },
  { key: 'R', desc: 'Reject sample' },
  { key: 'S', desc: 'Skip sample' },
  { key: '←', desc: 'Previous sample' },
  { key: '→', desc: 'Next sample' },
  { key: 'T', desc: 'Focus transcript editor' },
  { key: 'N', desc: 'Focus notes field' },
  { key: 'Ctrl+S', desc: 'Export data' },
  { key: 'Esc', desc: 'Blur active input' },
  { key: '?', desc: 'Toggle this help' },
];

export function ShortcutHelp({ onClose }: ShortcutHelpProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface-900 border border-surface-700/50 rounded-2xl shadow-2xl w-[420px] overflow-hidden animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-700/40">
          <h2 className="text-sm font-semibold text-surface-100 flex items-center gap-2">
            <Keyboard size={16} className="text-accent-400" />
            Keyboard Shortcuts
          </h2>
          <button onClick={onClose} className="text-surface-500 hover:text-surface-200">
            <X size={16} />
          </button>
        </div>
        <div className="p-5 grid grid-cols-2 gap-x-6 gap-y-2.5">
          {SHORTCUTS.map((s) => (
            <div key={s.key} className="flex items-center gap-3">
              <kbd className="shrink-0 px-2 py-0.5 bg-surface-800 border border-surface-700/50 rounded text-[11px] font-mono text-accent-300 min-w-[56px] text-center">
                {s.key}
              </kbd>
              <span className="text-[11px] text-surface-400">{s.desc}</span>
            </div>
          ))}
        </div>
        <div className="px-5 pb-4">
          <p className="text-[10px] text-surface-500 text-center">
            Shortcuts are disabled when typing in text fields. Press Esc to blur.
          </p>
        </div>
      </div>
    </div>
  );
}
