'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  PRIMARY_LEVER_ID_TO_NAME,
  RESEARCH_AREAS_MIN_YEAR,
  getPrimaryLeverOptions,
  parseResultYear,
} from '../constants';

interface PrimaryLeversCellProps {
  values: number[];
  /** Result year — decides whether Primary Levers or Research Areas are offered. */
  year: unknown;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: number[]) => void;
  disabled?: boolean;
}

export function PrimaryLeversCell({ values, year, globalIdx, onEdit, disabled }: PrimaryLeversCellProps) {
  const [showPopover, setShowPopover] = useState(false);
  const [search, setSearch] = useState('');
  const [popoverPos, setPopoverPos] = useState<{ top: number; left: number } | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const addBtnRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const parsedYear = parseResultYear(year);
  const options = useMemo(() => getPrimaryLeverOptions(year), [year]);
  const isResearchAreas = parsedYear !== null && parsedYear >= RESEARCH_AREAS_MIN_YEAR;
  const noun = isResearchAreas ? 'research area' : 'primary lever';

  useEffect(() => {
    if (!showPopover) return;
    setSearch('');
    setTimeout(() => searchRef.current?.focus(), 50);
  }, [showPopover]);

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

  // Close the picker when the year no longer offers options (year cleared)
  useEffect(() => {
    if (options.length === 0) setShowPopover(false);
  }, [options.length]);

  const getLabel = useCallback((id: number): string => PRIMARY_LEVER_ID_TO_NAME[id] ?? `Option ${id}`, []);

  const handleRemove = useCallback((id: number) => {
    onEdit(globalIdx, 'primary_levers', values.filter((v) => v !== id));
  }, [values, globalIdx, onEdit]);

  const handleAdd = useCallback((id: number) => {
    if (!values.includes(id)) {
      onEdit(globalIdx, 'primary_levers', [...values, id]);
    }
    setShowPopover(false);
  }, [values, globalIdx, onEdit]);

  const filtered = options
    .filter((o) => !values.includes(o.id))
    .filter((o) => o.name.toLowerCase().includes(search.toLowerCase()));

  if (disabled) {
    return (
      <div className="geo-cell levers-cell">
        <span className="geo-readonly">
          {values.length ? values.map(getLabel).join(', ') : '—'}
        </span>
      </div>
    );
  }

  return (
    <div className="geo-cell levers-cell">
      <div className="bulk-chips">
        {values.length === 0 && <span className="bulk-chips-empty">—</span>}
        {values.map((id) => (
          <span key={id} className="bulk-chip geo-chip" title={getLabel(id)}>
            <span className="bulk-chip-label">{getLabel(id)}</span>
            <button
              className="partner-chip-remove"
              aria-label={`Remove ${noun} ${getLabel(id)}`}
              onClick={() => handleRemove(id)}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      {options.length === 0 ? (
        <span className="levers-year-hint">Set the Year first</span>
      ) : (
        <div className="partner-add-container" ref={popoverRef}>
          <button
            ref={addBtnRef}
            className="partner-add-btn"
            aria-label={`Add ${noun}`}
            onClick={() => {
              if (!showPopover && addBtnRef.current) {
                const rect = addBtnRef.current.getBoundingClientRect();
                setPopoverPos({ top: rect.bottom + 4, left: rect.left });
              }
              setShowPopover((s) => !s);
            }}
          >
            +
          </button>
          {showPopover && popoverPos && (
            <div className="partners-search-popover" style={{ position: 'fixed', top: popoverPos.top, left: popoverPos.left }}>
              <div className="levers-popover-title">
                {isResearchAreas ? 'Research Areas' : 'Primary Levers'} · {parsedYear}
              </div>
              <div className="partners-search-input-wrap">
                <input
                  ref={searchRef}
                  className="partners-search-input"
                  placeholder={`Search ${noun}...`}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <ul className="partners-search-results">
                {filtered.length === 0 && (
                  <li className="partners-no-results">No options found</li>
                )}
                {filtered.map((o) => (
                  <li
                    key={o.id}
                    className="partners-search-result"
                    onClick={() => handleAdd(o.id)}
                  >
                    <span className="partners-result-name">{o.name}</span>
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
