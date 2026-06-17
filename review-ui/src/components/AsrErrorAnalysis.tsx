import { useReviewStore } from '../store/reviewStore';
import { clsx } from 'clsx';
import { Plus, Trash2, AlertTriangle, Tag } from 'lucide-react';
import type { ErrorCategory, AsrError } from '../types';
import { nanoid } from '../utils/nanoid';

const ERROR_CATEGORIES: { value: ErrorCategory; label: string }[] = [
  { value: 'spelling', label: 'Spelling' },
  { value: 'pronunciation', label: 'Pronunciation' },
  { value: 'missing_word', label: 'Missing word' },
  { value: 'extra_word', label: 'Extra word' },
  { value: 'hallucination', label: 'Hallucination' },
  { value: 'proper_noun', label: 'Proper noun' },
  { value: 'english_word', label: 'English word' },
  { value: 'code_mix', label: 'Code-mix' },
  { value: 'punctuation', label: 'Punctuation' },
  { value: 'speaker_overlap', label: 'Speaker overlap' },
  { value: 'background_noise', label: 'Background noise' },
  { value: 'music', label: 'Music' },
  { value: 'clipping', label: 'Clipping' },
  { value: 'other', label: 'Other' },
];

interface AsrErrorAnalysisProps {
  itemId: string;
}

export function AsrErrorAnalysis({ itemId }: AsrErrorAnalysisProps) {
  const annotation = useReviewStore((s) => s.getAnnotation(itemId));
  const addWrongWord = useReviewStore((s) => s.addWrongWord);
  const removeWrongWord = useReviewStore((s) => s.removeWrongWord);
  const updateWrongWord = useReviewStore((s) => s.updateWrongWord);
  const setErrorCategories = useReviewStore((s) => s.setErrorCategories);

  if (!annotation) return null;

  const { wrong_words, error_categories } = annotation;

  const handleAdd = () => {
    addWrongWord(itemId, { id: nanoid(), asr: '', correct: '' });
  };

  const handleFieldChange = (entry: AsrError, field: 'asr' | 'correct', val: string) => {
    updateWrongWord(itemId, { ...entry, [field]: val });
  };

  const toggleCategory = (cat: ErrorCategory) => {
    const next = error_categories.includes(cat)
      ? error_categories.filter((c) => c !== cat)
      : [...error_categories, cat];
    setErrorCategories(itemId, next);
  };

  return (
    <div className="bg-surface-800/40 rounded-xl border border-surface-700/30 overflow-hidden">
      <div className="px-4 py-3 border-b border-surface-700/30 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-surface-100 flex items-center gap-2">
          <AlertTriangle size={14} className="text-warning-400" />
          ASR Error Analysis
        </h3>
        <span className="text-[10px] text-surface-400">For assignment report</span>
      </div>

      <div className="p-4 space-y-4">
        {/* Wrong words table */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-[11px] text-surface-400 font-medium">ASR Error Pairs</label>
            <button
              onClick={handleAdd}
              className="flex items-center gap-1 text-[11px] text-accent-400 hover:text-accent-300 bg-accent-500/10 hover:bg-accent-500/20 px-2 py-1 rounded transition-colors"
            >
              <Plus size={11} /> Add Error
            </button>
          </div>

          {wrong_words.length === 0 ? (
            <p className="text-[11px] text-surface-500 italic text-center py-3">
              No ASR errors logged
            </p>
          ) : (
            <div className="space-y-2">
              {/* Header */}
              <div className="grid grid-cols-[1fr_1fr_32px] gap-2 text-[10px] text-surface-500 font-medium px-1">
                <span>ASR output</span>
                <span>Correct</span>
                <span />
              </div>
              {wrong_words.map((entry) => (
                <div key={entry.id} className="grid grid-cols-[1fr_1fr_32px] gap-2 items-center">
                  <input
                    value={entry.asr}
                    onChange={(e) => handleFieldChange(entry, 'asr', e.target.value)}
                    placeholder="ASR word…"
                    className="bg-surface-900/60 border border-surface-700/30 rounded px-2 py-1.5 text-xs text-danger-300 font-mono focus:outline-none focus:border-danger-500/40 placeholder:text-surface-600"
                    dir="auto"
                  />
                  <input
                    value={entry.correct}
                    onChange={(e) => handleFieldChange(entry, 'correct', e.target.value)}
                    placeholder="Correct word…"
                    className="bg-surface-900/60 border border-surface-700/30 rounded px-2 py-1.5 text-xs text-success-300 font-mono focus:outline-none focus:border-success-500/40 placeholder:text-surface-600"
                    dir="auto"
                  />
                  <button
                    onClick={() => removeWrongWord(itemId, entry.id)}
                    className="flex items-center justify-center text-surface-500 hover:text-danger-400 transition-colors"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Error categories */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Tag size={11} className="text-surface-500" />
            <label className="text-[11px] text-surface-400 font-medium">Error Categories</label>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ERROR_CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => toggleCategory(cat.value)}
                className={clsx(
                  'px-2.5 py-1 rounded-lg text-[10px] font-medium border transition-all',
                  error_categories.includes(cat.value)
                    ? 'bg-accent-500/20 border-accent-500/40 text-accent-300'
                    : 'bg-surface-800/60 border-surface-700/30 text-surface-500 hover:border-surface-600/40 hover:text-surface-300'
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
