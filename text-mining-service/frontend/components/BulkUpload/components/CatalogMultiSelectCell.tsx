'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type { CatalogOption } from '../constants';

interface CatalogMultiSelectCellProps {
  /** Selected catalog ids. */
  values: number[];
  /** Options available for this row — empty means the field cannot be filled yet. */
  options: CatalogOption[];
  /** Result field this cell writes to, e.g. "primary_levers". */
  field: string;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: number[]) => void;
  disabled?: boolean;
  /** Resolves a chip label, including ids no longer present in `options`. */
  labelFor: (id: number) => string;
  /** Singular noun for aria labels and the search placeholder. */
  noun: string;
  /** Heading shown above the option list. */
  popoverTitle: string;
  /** Replaces the + button when there are no options to offer. */
  emptyHint: string;
}

/**
 * Chips + searchable popover for a fixed catalog of numeric ids.
 * The caller resolves which options apply (usually from the result's year);
 * this component only renders and edits the selection.
 */
export function CatalogMultiSelectCell({
  values,
  options,
  field,
  globalIdx,
  onEdit,
  disabled,
  labelFor,
  noun,
  popoverTitle,
  emptyHint,
}: CatalogMultiSelectCellProps) {
  const [showPopover, setShowPopover] = useState(false);
  const [search, setSearch] = useState('');
  const [popoverPos, setPopoverPos] = useState<{ top: number; left: number } | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const addBtnRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

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

  // Close the picker when the row stops offering options (e.g. the year changed)
  useEffect(() => {
    if (options.length === 0) setShowPopover(false);
  }, [options.length]);

  const handleRemove = useCallback((id: number) => {
    onEdit(globalIdx, field, values.filter((v) => v !== id));
  }, [values, field, globalIdx, onEdit]);

  const handleAdd = useCallback((id: number) => {
    if (!values.includes(id)) {
      onEdit(globalIdx, field, [...values, id]);
    }
    setShowPopover(false);
  }, [values, field, globalIdx, onEdit]);

  const filtered = options
    .filter((o) => !values.includes(o.id))
    .filter((o) => o.name.toLowerCase().includes(search.toLowerCase()));

  if (disabled) {
    return (
      <div className="geo-cell catalog-cell">
        <span className="geo-readonly">
          {values.length ? values.map(labelFor).join(', ') : '—'}
        </span>
      </div>
    );
  }

  return (
    <div className="geo-cell catalog-cell">
      <div className="bulk-chips">
        {values.length === 0 && <span className="bulk-chips-empty">—</span>}
        {values.map((id) => (
          <span key={id} className="bulk-chip geo-chip" title={labelFor(id)}>
            <span className="bulk-chip-label">{labelFor(id)}</span>
            <button
              className="partner-chip-remove"
              aria-label={`Remove ${noun} ${labelFor(id)}`}
              onClick={() => handleRemove(id)}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      {options.length === 0 ? (
        <span className="catalog-year-hint">{emptyHint}</span>
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
              <div className="catalog-popover-title">{popoverTitle}</div>
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
