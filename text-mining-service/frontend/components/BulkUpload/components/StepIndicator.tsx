'use client';

import type { AppStep } from '../types';

const STEPS: { key: AppStep; label: string }[] = [
  { key: 'upload',   label: 'Select file' },
  { key: 'results',  label: 'Review and submit' },
  { key: 'unmapped', label: 'Unmapped institutions' },
  { key: 'summary',  label: 'Summary' },
];

const STEP_INDEX: Record<AppStep, number> = {
  upload:   0,
  results:  1,
  unmapped: 2,
  summary:  3,
};

interface StepIndicatorProps {
  currentStep: AppStep;
}

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  const current = STEP_INDEX[currentStep];

  return (
    <div className="bulk-step-indicator">
      {STEPS.map((step, i) => {
        const state = i < current ? 'done' : i === current ? 'active' : 'upcoming';
        return (
          <div key={step.key} className="bulk-step-item">
            {/* Connector line before this step */}
            {i > 0 && (
              <div className={`bulk-step-line bulk-step-line-${i <= current ? 'done' : 'upcoming'}`} />
            )}
            <div className="bulk-step-node">
              <div className={`bulk-step-circle bulk-step-circle-${state}`}>
                {i + 1}
              </div>
              <span className={`bulk-step-label${state === 'active' ? ' bulk-step-label-active' : ''}`}>
                {step.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
