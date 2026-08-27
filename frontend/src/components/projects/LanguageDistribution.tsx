import React from 'react';
import { LanguageStat } from '../../types';
import { Code2 } from 'lucide-react';

interface LanguageDistributionProps {
  languages: Record<string, LanguageStat>;
  categories?: Record<string, { files: number; lines: number }>;
  totalLines: number;
}

const LANGUAGE_BAR_COLORS: Record<string, string> = {
  Python: 'bg-emerald-500',
  TypeScript: 'bg-blue-500',
  JavaScript: 'bg-amber-400',
  HTML: 'bg-orange-500',
  CSS: 'bg-cyan-400',
  SCSS: 'bg-pink-500',
  JSON: 'bg-amber-600',
  YAML: 'bg-purple-400',
  SQL: 'bg-indigo-400',
  Markdown: 'bg-slate-400',
  Rust: 'bg-orange-600',
  Go: 'bg-teal-400',
  Java: 'bg-red-500',
  'C#': 'bg-violet-600',
  'C++': 'bg-blue-600',
  C: 'bg-slate-500',
  PHP: 'bg-indigo-500',
  Shell: 'bg-lime-500',
  Dockerfile: 'bg-sky-500',
};

const getBarColor = (lang: string): string => {
  return LANGUAGE_BAR_COLORS[lang] || 'bg-slate-600';
};

export const LanguageDistribution: React.FC<LanguageDistributionProps> = ({
  languages,
  categories,
  totalLines,
}) => {
  const sortedLanguages = Object.entries(languages).sort(
    (a, b) => b[1].lines - a[1].lines
  );

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white tracking-tight uppercase">
              Language Composition & Code Density
            </h3>
            <span className="text-[11px] text-slate-400">
              {totalLines.toLocaleString()} Total Lines of Code
            </span>
          </div>
        </div>

        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
          {sortedLanguages.length} Languages
        </span>
      </div>

      {/* Multi-color Stacked Progress Bar */}
      <div className="w-full bg-slate-950 rounded-full h-3 flex overflow-hidden p-0.5 border border-slate-800">
        {sortedLanguages.map(([lang, stat]) => (
          <div
            key={lang}
            className={`${getBarColor(lang)} h-full first:rounded-l-full last:rounded-r-full transition-all duration-300`}
            style={{ width: `${Math.max(stat.percentage, 1.5)}%` }}
            title={`${lang}: ${stat.lines.toLocaleString()} lines (${stat.percentage}%)`}
          />
        ))}
      </div>

      {/* Detailed Language Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5 pt-2">
        {sortedLanguages.map(([lang, stat]) => (
          <div
            key={lang}
            className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${getBarColor(lang)}`} />
              <div>
                <div className="text-xs font-semibold text-white">{lang}</div>
                <div className="text-[10px] text-slate-400 font-mono">
                  {stat.files} {stat.files === 1 ? 'file' : 'files'}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-mono font-bold text-slate-200">
                {stat.percentage}%
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                {stat.lines.toLocaleString()} L
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Category breakdown tags */}
      {categories && Object.keys(categories).length > 0 && (
        <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-slate-400 font-mono uppercase">
            File Breakdown:
          </span>
          {Object.entries(categories).map(([cat, info]) => (
            <span
              key={cat}
              className="text-[10px] font-mono px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300"
            >
              <strong className="text-white capitalize">{cat.replace('_', ' ')}</strong>: {info.files} files ({info.lines.toLocaleString()} L)
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
