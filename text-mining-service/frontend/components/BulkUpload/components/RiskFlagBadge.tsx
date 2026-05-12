'use client';

import { useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';

const TOOLTIP_TEXT = 'High-risk field — AI may make mistakes here. Review carefully.';

export function RiskFlagBadge() {
  const badgeRef = useRef<HTMLSpanElement>(null);
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (!badgeRef.current) return;
    const rect = badgeRef.current.getBoundingClientRect();
    const left = Math.min(rect.left + rect.width / 2 - 100, window.innerWidth - 216);
    const spaceAbove = rect.top;
    const top = spaceAbove >= 50 ? rect.top - 44 : rect.bottom + 6;
    setTooltipPos({ top, left });
  }, []);

  const handleMouseLeave = useCallback(() => setTooltipPos(null), []);

  return (
    <>
      <span
        ref={badgeRef}
        className="risk-flag-icon"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        !
      </span>

      {tooltipPos !== null &&
        createPortal(
          <div className="risk-flag-tooltip" style={{ top: tooltipPos.top, left: tooltipPos.left }}>
            {TOOLTIP_TEXT}
          </div>,
          document.body,
        )}
    </>
  );
}
