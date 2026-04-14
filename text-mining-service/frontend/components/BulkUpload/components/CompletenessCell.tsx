'use client';

import { useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { CompletenessResult } from '../utils/completenessChecker';

interface CompletenessCellProps {
  completeness: CompletenessResult;
}

export function CompletenessCell({ completeness }: CompletenessCellProps) {
  const { isComplete, reasons } = completeness;
  const badgeRef = useRef<HTMLSpanElement>(null);
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (isComplete || !badgeRef.current) return;
    const rect = badgeRef.current.getBoundingClientRect();
    const left = Math.min(rect.left, window.innerWidth - 316);
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow >= 160 ? rect.bottom + 6 : rect.top - 8;
    setTooltipPos({ top, left });
  }, [isComplete]);

  const handleMouseLeave = useCallback(() => setTooltipPos(null), []);

  return (
    <div className="completeness-cell">
      <span
        ref={badgeRef}
        className={`completeness-badge ${isComplete ? 'completeness-complete' : 'completeness-incomplete'}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {isComplete ? '✓ Complete' : '⚠ Incomplete'}
      </span>

      {tooltipPos !== null &&
        createPortal(
          <div
            className="completeness-tooltip"
            style={{ top: tooltipPos.top, left: tooltipPos.left }}
          >
            <p className="completeness-tooltip-title">Missing or invalid fields:</p>
            <ul className="completeness-tooltip-list">
              {reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>,
          document.body,
        )}
    </div>
  );
}
