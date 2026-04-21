'use client';

import { useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';

const FIXED_TIPS = [
  'A result with the same title may already exist in STAR.',
  'The contract code may not exist or may be incorrect.',
  'Required fields (title, year, training type) may be missing or invalid.',
  'The STAR session may have expired — try re-submitting.',
  'Contact the STAR team if the error persists.',
];

interface FailedStatusBadgeProps {
  errorMessage?: string;
}

export function FailedStatusBadge({ errorMessage }: FailedStatusBadgeProps) {
  const badgeRef = useRef<HTMLSpanElement>(null);
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (!badgeRef.current) return;
    const rect = badgeRef.current.getBoundingClientRect();
    const left = Math.min(rect.left, window.innerWidth - 316);
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow >= 200 ? rect.bottom + 6 : rect.top - 8;
    setTooltipPos({ top, left });
  }, []);

  const handleMouseLeave = useCallback(() => setTooltipPos(null), []);

  return (
    <>
      <span
        ref={badgeRef}
        className="status-failed"
        style={{ cursor: 'help' }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        ⓘ Failed
      </span>

      {tooltipPos !== null &&
        createPortal(
          <div className="failed-tooltip" style={{ top: tooltipPos.top, left: tooltipPos.left }}>
            {errorMessage && (
              <p className="failed-tooltip-error">{errorMessage}</p>
            )}
            <p className="failed-tooltip-title">Possible causes:</p>
            <ul className="failed-tooltip-list">
              {FIXED_TIPS.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </div>,
          document.body,
        )}
    </>
  );
}
