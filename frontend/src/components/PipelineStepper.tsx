import React from 'react';
import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';
import { PipelineProgress } from '../types';

interface PipelineStepperProps {
  progress: PipelineProgress;
}

const STAGES = [
  { id: 1, name: 'Extraction', desc: 'Unpack source files' },
  { id: 2, name: 'Languages', desc: 'Detect stack & frameworks' },
  { id: 3, name: 'Code AST', desc: 'Parse classes & symbols' },
  { id: 4, name: 'Structure', desc: 'Analyze folder hierarchy' },
  { id: 5, name: 'Dependencies', desc: 'Map internal imports' },
  { id: 6, name: 'API Endpoints', desc: 'Discover REST routes' },
  { id: 7, name: 'Database', desc: 'Parse ORM & SQL models' },
  { id: 8, name: 'Knowledge Graph', desc: 'Connect components' },
  { id: 9, name: 'Documentation', desc: 'Synthesize markdown docs' },
  { id: 10, name: 'Diagrams', desc: 'Generate Mermaid & Flow' },
  { id: 11, name: 'Vector Index', desc: 'Embeddings & RAG' },
];

export const PipelineStepper: React.FC<PipelineStepperProps> = ({ progress }) => {
  const currentPercent = progress.progress_percent ?? 0;
  const isFailed = progress.status === 'failed' || progress.status === 'FAILED';
  const isCompleted = progress.status === 'completed' || progress.status === 'READY' || progress.status === 'ANALYZED';


  // Estimate active step index (0-based) based on percentage
  const activeIndex = Math.min(
    Math.floor((currentPercent / 100) * STAGES.length),
    STAGES.length - 1
  );

  return (
    <div className="w-full bg-[#111827]/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="text-lg font-bold text-white tracking-tight">Intelligence Pipeline</h3>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                isCompleted
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : isFailed
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  : 'bg-brand-500/10 text-brand-400 border-brand-500/30 animate-pulse'
              }`}
            >
              {isCompleted ? 'Completed' : isFailed ? 'Failed' : 'Processing'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">{progress.current_step}</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-2xl font-black text-white">{currentPercent}%</span>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mb-8 relative">
        <div
          className={`h-full transition-all duration-500 ease-out rounded-full ${
            isFailed
              ? 'bg-rose-500'
              : 'bg-gradient-to-r from-brand-500 via-indigo-500 to-cyan-400'
          }`}
          style={{ width: `${currentPercent}%` }}
        />
      </div>

      {/* Horizontal Steps Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-11 gap-3">
        {STAGES.map((stage, idx) => {
          const isDone = isCompleted || idx < activeIndex;
          const isCurrent = !isCompleted && !isFailed && idx === activeIndex;

          return (
            <div
              key={stage.id}
              className={`p-2.5 rounded-xl border transition-all text-left flex flex-col justify-between ${
                isDone
                  ? 'bg-slate-900/60 border-emerald-500/30 text-slate-300'
                  : isCurrent
                  ? 'bg-brand-950/40 border-brand-500/60 text-white shadow-md shadow-brand-500/10 ring-1 ring-brand-500/40'
                  : 'bg-slate-900/20 border-slate-800/60 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono font-bold text-slate-400">0{stage.id}</span>
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-brand-400 animate-spin" />
                ) : (
                  <Circle className="w-3.5 h-3.5 text-slate-700" />
                )}
              </div>
              <div>
                <p className={`text-xs font-semibold truncate ${isCurrent ? 'text-brand-300' : ''}`}>
                  {stage.name}
                </p>
                <p className="text-[10px] text-slate-500 truncate mt-0.5">{stage.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {isFailed && progress.error_message && (
        <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center gap-3 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{progress.error_message}</span>
        </div>
      )}
    </div>
  );
};
