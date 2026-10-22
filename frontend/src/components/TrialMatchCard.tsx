/**
 * frontend/src/components/TrialMatchCard.tsx
 */
import React, { useState } from 'react';
import type { TrialMatchScore } from '../services/api';
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, Activity } from 'lucide-react';

interface TrialMatchCardProps {
  match: TrialMatchScore;
}

export const TrialMatchCard: React.FC<TrialMatchCardProps> = ({ match }) => {
  const [expanded, setExpanded] = useState<boolean>(false);

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 dark:text-emerald-400 border-emerald-200';
    if (score >= 0.5) return 'text-amber-600 bg-amber-50 dark:bg-amber-950/50 dark:text-amber-400 border-amber-200';
    return 'text-rose-600 bg-rose-50 dark:bg-rose-950/50 dark:text-rose-400 border-rose-200';
  };

  const scorePct = Math.round(match.match_score * 100);

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4 hover:border-slate-300 dark:hover:border-slate-700 transition-all">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs text-indigo-600 dark:text-indigo-400 font-bold uppercase tracking-wider">
              {match.trial_id}
            </span>
            {match.eligible ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                <CheckCircle2 className="w-3 h-3" /> Eligible Candidate
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300">
                <XCircle className="w-3 h-3" /> Ineligible
              </span>
            )}
          </div>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-base leading-snug">
            {match.trial_title}
          </h3>
        </div>

        {/* Score Radial / Badge */}
        <div
          className={`flex flex-col items-center justify-center min-w-[70px] p-2 rounded-xl border font-bold ${getScoreColor(
            match.match_score
          )}`}
        >
          <span className="text-xl font-mono">{scorePct}%</span>
          <span className="text-[10px] uppercase tracking-wider font-sans font-semibold">Match</span>
        </div>
      </div>

      {/* Criterion Breakdown Toggle */}
      {match.evaluations && match.evaluations.length > 0 && (
        <div className="border-t border-slate-100 dark:border-slate-800 pt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center justify-between w-full text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              Criterion Matching Breakdown ({match.evaluations.length} Evaluated)
            </span>
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {expanded && (
            <div className="mt-3 space-y-2">
              {match.evaluations.map((evalItem, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-slate-50 dark:bg-slate-950/60 rounded-lg border border-slate-100 dark:border-slate-800 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {evalItem.criterion_text}
                    </span>
                    {evalItem.is_met ? (
                      <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Met
                      </span>
                    ) : (
                      <span className="text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-1">
                        <XCircle className="w-3 h-3" /> Unmet
                      </span>
                    )}
                  </div>
                  <p className="text-slate-500 dark:text-slate-400 leading-relaxed">
                    {evalItem.reasoning}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};