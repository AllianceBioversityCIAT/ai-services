'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

// Internal value ↔ display label
const SDG_KEYS = Array.from({ length: 17 }, (_, i) => `SDG${i + 1}`);
const SDG_LABEL: Record<string, string> = Object.fromEntries(
  SDG_KEYS.map(k => [k, `SDG Goal ${k.replace('SDG', '')}`])
);

interface SdgCellProps {
  values: string[];
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: string[]) => void;
}

export function SdgCell({ values, globalIdx, onEdit }: SdgCellProps) {
  const [showPopover, setShowPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showPopover) return;
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowPopover(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showPopover]);

  const handleRemove = useCallback((key: string) => {
    onEdit(globalIdx, 'sdg_targets', values.filter(v => v !== key));
  }, [values, globalIdx, onEdit]);

  const handleAdd = useCallback((key: string) => {
    if (!values.includes(key)) {
      onEdit(globalIdx, 'sdg_targets', [...values, key]);
    }
    setShowPopover(false);
  }, [values, globalIdx, onEdit]);

  const available = SDG_KEYS.filter(k => !values.includes(k));

  return (
    <div className="sdg-cell">
      <div className="bulk-chips">
        {values.length === 0 && <span className="bulk-chips-empty">—</span>}
        {values.map(key => (
          <span key={key} className="bulk-chip sdg-chip">
            {SDG_LABEL[key] ?? key}
            <button
              className="partner-chip-remove"
              aria-label={`Remove ${SDG_LABEL[key] ?? key}`}
              onClick={() => handleRemove(key)}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      {available.length > 0 && (
        <div className="partner-add-container" ref={popoverRef}>
          <button
            className="partner-add-btn"
            aria-label="Add SDG target"
            onClick={() => setShowPopover(s => !s)}
          >
            +
          </button>
          {showPopover && (
            <div className="partners-search-popover sdg-popover">
              <ul className="partners-search-results">
                {available.map(k => (
                  <li
                    key={k}
                    className="partners-search-result"
                    onClick={() => handleAdd(k)}
                  >
                    <span className="partners-result-name">{SDG_LABEL[k]}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
