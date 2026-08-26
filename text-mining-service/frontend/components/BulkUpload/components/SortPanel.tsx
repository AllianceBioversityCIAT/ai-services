'use client';

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import type { ColumnDef, TabType, TableSortConfig } from '../types';
import { getColumnLabel, getSortColumnKey, getSortDirectionLabels } from '../utils/tableHelpers';

const PANEL_WIDTH = 300;
const VIEWPORT_MARGIN = 8;
const ANCHOR_GAP = 5;
const FALLBACK_PANEL_HEIGHT = 260;

interface SortPanelProps {
  columns: ColumnDef[];
  currentTab: TabType;
  currentSort: TableSortConfig | null;
  anchorRef: RefObject<HTMLElement | null>;
  onApply: (config: TableSortConfig) => void;
  onClear: () => void;
  onClose: () => void;
}

function getPopoverPosition(anchorRect: DOMRect, panelHeight: number, panelWidth: number) {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  // Align panel's right edge with the anchor (button sits on the right of the tabs row)
  let left = anchorRect.right - panelWidth;
  left = Math.max(VIEWPORT_MARGIN, Math.min(left, viewportWidth - panelWidth - VIEWPORT_MARGIN));

  let top = anchorRect.bottom + ANCHOR_GAP;
  if (top + panelHeight > viewportHeight - VIEWPORT_MARGIN) {
    top = anchorRect.top - panelHeight - ANCHOR_GAP;
  }
  top = Math.max(VIEWPORT_MARGIN, Math.min(top, viewportHeight - panelHeight - VIEWPORT_MARGIN));

  return { top, left };
}

export function SortPanel({
  columns,
  currentTab,
  currentSort,
  anchorRef,
  onApply,
  onClear,
  onClose,
}: SortPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const defaultColumnKey = currentSort?.columnKey ?? getSortColumnKey(columns[0]);
  const [columnKey, setColumnKey] = useState(defaultColumnKey);
  const [direction, setDirection] = useState<TableSortConfig['direction']>(currentSort?.direction ?? 'asc');
  const [position, setPosition] = useState({ top: 0, left: 0 });

  const selectedColumn = columns.find((col) => getSortColumnKey(col) === columnKey) ?? columns[0];
  const directionLabels = getSortDirectionLabels(columnKey, selectedColumn?.type);

  const updatePosition = useCallback(() => {
    const anchor = anchorRef.current;
    if (!anchor) return;
    const panelHeight = panelRef.current?.offsetHeight ?? FALLBACK_PANEL_HEIGHT;
    setPosition(getPopoverPosition(anchor.getBoundingClientRect(), panelHeight, PANEL_WIDTH));
  }, [anchorRef]);

  useLayoutEffect(() => {
    updatePosition();
  }, [updatePosition, columnKey, direction]);

  useEffect(() => {
    const onScrollOrResize = () => updatePosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [updatePosition]);

  useEffect(() => {
    const anchor = anchorRef.current;
    if (!anchor || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => updatePosition());
    observer.observe(anchor);
    return () => observer.disconnect();
  }, [anchorRef, updatePosition]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [anchorRef, onClose]);

  const handleApply = useCallback(() => {
    if (!columnKey) return;
    onApply({ columnKey, direction });
    onClose();
  }, [columnKey, direction, onApply, onClose]);

  const handleClear = useCallback(() => {
    onClear();
    onClose();
  }, [onClear, onClose]);

  const style: React.CSSProperties = {
    position: 'fixed',
    top: position.top,
    left: position.left,
    zIndex: 9999,
    background: 'white',
    border: '1px solid var(--bulk-gray-300)',
    borderRadius: 6,
    boxShadow: 'var(--bulk-shadow-md)',
    width: PANEL_WIDTH,
  };

  if (typeof document === 'undefined') return null;

  return createPortal(
    <div ref={panelRef} className="sort-panel" style={style}>
      <div className="sort-panel-header">
        <span className="sort-panel-title">Sort by</span>
      </div>
      <div className="sort-panel-body">
        <label className="sort-panel-field">
          <span className="sort-panel-label">Field</span>
          <select
            className="sort-panel-select"
            value={columnKey}
            onChange={(e) => setColumnKey(e.target.value)}
          >
            {columns.map((col) => {
              const key = getSortColumnKey(col);
              return (
                <option key={key} value={key}>
                  {getColumnLabel(col, currentTab)}
                </option>
              );
            })}
          </select>
        </label>
        <fieldset className="sort-panel-direction">
          <legend className="sort-panel-label">Order</legend>
          <label className="sort-direction-option">
            <input
              type="radio"
              name="sort-direction"
              checked={direction === 'asc'}
              onChange={() => setDirection('asc')}
            />
            <span>{directionLabels.asc}</span>
          </label>
          <label className="sort-direction-option">
            <input
              type="radio"
              name="sort-direction"
              checked={direction === 'desc'}
              onChange={() => setDirection('desc')}
            />
            <span>{directionLabels.desc}</span>
          </label>
        </fieldset>
      </div>
      <div className="sort-panel-footer">
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
