'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';

interface FilterPanelProps {
  columnKey: string;
  uniqueValues: string[];
  currentFilters: string[];
  anchorRect: DOMRect;
  onApply: (columnKey: string, values: string[]) => void;
  onClear: (columnKey: string) => void;
  onClose: () => void;
}

export function FilterPanel({
  columnKey,
  uniqueValues,
  currentFilters,
  anchorRect,
  onApply,
  onClear,
  onClose,
}: FilterPanelProps) {
  const [search, setSearch] = useState('');
  // rerender-lazy-state-init: initialise from prop (only on mount)
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(currentFilters.length === 0 ? uniqueValues : currentFilters),
  );
  const panelRef = useRef<HTMLDivElement>(null);

  const visibleValues = search
    ? uniqueValues.filter((v) => v.toLowerCase().includes(search.toLowerCase()))
    : uniqueValues;

  const allVisible = visibleValues.every((v) => selected.has(v));

  const toggleAll = useCallback(() => {
    // rerender-functional-setstate
    setSelected((prev) => {
      const next = new Set(prev);
      if (allVisible) {
        visibleValues.forEach((v) => next.delete(v));
      } else {
        visibleValues.forEach((v) => next.add(v));
      }
      return next;
    });
  }, [allVisible, visibleValues]);

  const toggleValue = useCallback((value: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }, []);

  // Close on outside click (client-event-listeners)
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose]);

  const handleApply = () => {
    const values = Array.from(selected);
    if (values.length === uniqueValues.length) {
      onClear(columnKey);
    } else if (values.length > 0) {
      onApply(columnKey, values);
    } else {
      onApply(columnKey, []);
    }
    onClose();
  };

  const handleClear = () => {
    onClear(columnKey);
    onClose();
  };

  const style: React.CSSProperties = {
    position: 'fixed',
    top: anchorRect.bottom + 5,
    left: anchorRect.left,
    zIndex: 9999,
    background: 'white',
    border: '1px solid var(--bulk-gray-300)',
    borderRadius: 6,
    boxShadow: 'var(--bulk-shadow-md)',
    minWidth: 220,
    maxWidth: 320,
  };

  // Use portal to render above all stacking contexts
  if (typeof document === 'undefined') return null;

  return createPortal(
    <div ref={panelRef} className="filter-panel" style={style}>
      <div className="filter-panel-header">
        <input
          type="text"
          className="filter-search"
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          autoFocus
        />
      </div>
      <div className="filter-options" style={{ maxHeight: 240, overflowY: 'auto' }}>
        <label className="filter-option">
          <input type="checkbox" checked={allVisible} onChange={toggleAll} />
          <span>(Select All)</span>
        </label>
        {visibleValues.map((value) => (
          <label key={value} className="filter-option">
            <input
              type="checkbox"
              checked={selected.has(value)}
              onChange={() => toggleValue(value)}
            />
            <span>{value}</span>
          </label>
        ))}
      </div>
      <div className="filter-panel-footer">
        <button className="filter-btn filter-btn-clear" type="button" onClick={handleClear}>
          Clear
        </button>
        <button className="filter-btn filter-btn-apply" type="button" onClick={handleApply}>
          Apply
        </button>
      </div>
    </div>,
    document.body,
  );
}
