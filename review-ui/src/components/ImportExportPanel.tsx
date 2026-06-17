import React, { useCallback, useState } from 'react';
import { useReviewStore } from '../store/reviewStore';
import { parseJsonlFile, parseImportFile, exportData } from '../utils/dataUtils';
import { clsx } from 'clsx';
import {
  Upload,
  FolderOpen,
  Download,
  RefreshCw,
  Database,
  FileJson,
  Zap,
} from 'lucide-react';
import type { ExportScope } from '../types';

export function ImportExportPanel() {
  const { loadSegments, importAnnotations, items, getFilteredItems, datasetName } = useReviewStore();

  const [isDragging, setIsDragging] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [exportScope, setExportScope] = useState<ExportScope>('all');
  const [exportFormat, setExportFormat] = useState<'json' | 'csv'>('json');

  // ── Import dataset JSONL ────────────────────────────────────────────────────

  const handleDatasetFile = useCallback(
    async (file: File) => {
      try {
        setImportStatus('Loading…');
        const segments = await parseJsonlFile(file);
        loadSegments(segments, file.name.replace(/\.(jsonl|json)$/, ''));
        setImportStatus(`✓ Loaded ${segments.length} segments from ${file.name}`);
      } catch (err) {
        setImportStatus(`✗ Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    },
    [loadSegments]
  );

  // ── Import previous review session ────────────────────────────────────────

  const handleAnnotationFile = useCallback(
    async (file: File) => {
      try {
        setImportStatus('Merging annotations…');
        const annotations = await parseImportFile(file);
        importAnnotations(annotations, true);
        setImportStatus(`✓ Merged ${annotations.length} annotations, resuming from last reviewed`);
      } catch (err) {
        setImportStatus(`✗ Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    },
    [importAnnotations]
  );

  // ── Drag and drop ─────────────────────────────────────────────────────────

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (!file) return;
      if (file.name.endsWith('.jsonl')) {
        handleDatasetFile(file);
      } else if (file.name.endsWith('.json')) {
        handleAnnotationFile(file);
      }
    },
    [handleDatasetFile, handleAnnotationFile]
  );

  // ── Export ────────────────────────────────────────────────────────────────

  const handleExport = () => {
    const filteredIds = new Set(getFilteredItems().map((i) => i.id));
    exportData(items, exportFormat, exportScope, filteredIds);
  };

  return (
    <div className="min-h-screen bg-surface-950 text-surface-100 p-8">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-surface-50 flex items-center gap-3">
            <Database size={24} className="text-accent-400" />
            Dataset Manager
          </h1>
          <p className="text-surface-400 text-sm mt-1">
            Import segments, resume sessions, and export results.
          </p>
        </div>

        {/* Current dataset info */}
        {datasetName && (
          <div className="bg-surface-800/40 border border-surface-700/30 rounded-xl px-4 py-3 flex items-center gap-3">
            <Zap size={16} className="text-accent-400" />
            <div>
              <p className="text-xs font-medium text-surface-200">{datasetName}</p>
              <p className="text-[11px] text-surface-400">{items.length} segments loaded</p>
            </div>
          </div>
        )}

        {/* Import dataset JSONL */}
        <Section title="Import Dataset" icon={<Upload size={16} />}>
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={clsx(
              'border-2 border-dashed rounded-xl p-8 text-center transition-all',
              isDragging
                ? 'border-accent-500/70 bg-accent-500/5'
                : 'border-surface-700/40 hover:border-surface-600/50 bg-surface-800/20'
            )}
          >
            <FolderOpen size={32} className="mx-auto text-surface-500 mb-3" />
            <p className="text-sm text-surface-300 mb-1">Drag & drop a <code className="text-accent-300">.jsonl</code> file here</p>
            <p className="text-xs text-surface-500 mb-4">
              or use the button below to browse
            </p>
            <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-accent-500 hover:bg-accent-400 text-white text-sm font-medium rounded-lg transition-colors">
              <Upload size={14} />
              Browse JSONL file
              <input
                type="file"
                accept=".jsonl,.json"
                className="sr-only"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleDatasetFile(file);
                  e.target.value = '';
                }}
              />
            </label>
          </div>
        </Section>

        {/* Import previous session */}
        <Section title="Resume Session" icon={<RefreshCw size={16} />}>
          <p className="text-xs text-surface-400 mb-3">
            Import a previously exported <code className="text-accent-300">.json</code> review file.
            Existing work is preserved — only new or updated annotations are merged.
          </p>
          <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-surface-700/60 hover:bg-surface-600/60 text-surface-200 text-sm font-medium rounded-lg transition-colors border border-surface-700/30">
            <FileJson size={14} />
            Import Review Session
            <input
              type="file"
              accept=".json,.jsonl"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleAnnotationFile(file);
                e.target.value = '';
              }}
            />
          </label>
        </Section>

        {/* Export */}
        <Section title="Export Results" icon={<Download size={16} />}>
          <div className="grid grid-cols-2 gap-4 mb-4">
            {/* Scope */}
            <div>
              <label className="text-[11px] text-surface-400 font-medium mb-1.5 block">Scope</label>
              <div className="space-y-1.5">
                {(['all', 'reviewed', 'approved', 'rejected', 'filtered'] as ExportScope[]).map((s) => (
                  <label key={s} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="scope"
                      value={s}
                      checked={exportScope === s}
                      onChange={() => setExportScope(s)}
                      className="accent-accent-500"
                    />
                    <span className="text-xs text-surface-300 capitalize">{s}</span>
                  </label>
                ))}
              </div>
            </div>
            {/* Format */}
            <div>
              <label className="text-[11px] text-surface-400 font-medium mb-1.5 block">Format</label>
              <div className="space-y-1.5">
                {(['json', 'csv'] as const).map((f) => (
                  <label key={f} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="format"
                      value={f}
                      checked={exportFormat === f}
                      onChange={() => setExportFormat(f)}
                      className="accent-accent-500"
                    />
                    <span className="text-xs text-surface-300 uppercase">{f}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <button
            onClick={handleExport}
            disabled={items.length === 0}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent-500 hover:bg-accent-400 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
          >
            <Download size={15} />
            Export {exportFormat.toUpperCase()}
          </button>
        </Section>

        {/* Status message */}
        {importStatus && (
          <div className={clsx(
            'text-xs px-4 py-3 rounded-lg border',
            importStatus.startsWith('✓')
              ? 'bg-success-500/10 border-success-500/20 text-success-300'
              : importStatus.startsWith('✗')
              ? 'bg-danger-500/10 border-danger-500/20 text-danger-300'
              : 'bg-accent-500/10 border-accent-500/20 text-accent-300'
          )}>
            {importStatus}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-surface-900/40 border border-surface-700/30 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-surface-700/30">
        <span className="text-accent-400">{icon}</span>
        <h2 className="text-sm font-semibold text-surface-100">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}
