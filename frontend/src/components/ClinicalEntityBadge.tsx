/**
 * frontend/src/components/ClinicalEntityBadge.tsx
 */
import React from 'react';
import type { ExtractedClinicalEntity } from '../services/api';

interface ClinicalEntityBadgeProps {
  entity: ExtractedClinicalEntity;
}

export const ClinicalEntityBadge: React.FC<ClinicalEntityBadgeProps> = ({ entity }) => {
  const getBadgeStyle = (category: string) => {
    const catLower = category.toLowerCase();
    if (catLower.includes('disease') || catLower.includes('condition') || catLower.includes('problem')) {
      return 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800';
    }
    if (catLower.includes('medication') || catLower.includes('drug') || catLower.includes('treatment')) {
      return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800';
    }
    if (catLower.includes('procedure') || catLower.includes('test') || catLower.includes('lab')) {
      return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800';
    }
    return 'bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700';
  };

  const confidencePct = Math.round(entity.confidence_score * 100);

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${getBadgeStyle(
        entity.entity_group
      )}`}
    >
      <span className="font-semibold">{entity.text}</span>
      <span className="opacity-60 text-[10px]">({entity.entity_group})</span>
      <span className="ml-1 px-1 py-0.2 bg-black/5 dark:bg-white/10 rounded text-[10px] font-mono">
        {confidencePct}%
      </span>
    </span>
  );
};