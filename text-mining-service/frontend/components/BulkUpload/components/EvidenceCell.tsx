'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

export interface Evidence {
  evidence_description: string;
  evidence_link: string;
}

interface EvidenceCellProps {
  evidences: Evidence[];
  field: 'evidence_description' | 'evidence_link';
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: Evidence[]) => void;
}

export function EvidenceCell({ evidences, field, globalIdx, onEdit }: EvidenceCellProps) {
  const [showPopover, setShowPopover] = useState(false);
  const [editValues, setEditValues] = useState<string[]>([]);
  const popoverRef = useRef<HTMLDivElement>(null);

  const isLink = field === 'evidence_link';
  const displayItems = evidences.map(e => e[field]).filter(Boolean);

  const openPopover = useCallback(() => {
    // Initialize with current values; always at least one empty row
    const vals = evidences.map(e => e[field] ?? '');
    setEditValues(vals.length > 0 ? vals : ['']);
    setShowPopover(true);
  }, [evidences, field]);

  const saveAndClose = useCallback(() => {
    // Merge edited values back into the evidences array, preserving the other field
    const maxLen = Math.max(evidences.length, editValues.length);
    const updated: Evidence[] = [];
    for (let i = 0; i < maxLen; i++) {
      const existing = evidences[i] ?? { evidence_description: '', evidence_link: '' };
      updated.push({ ...existing, [field]: editValues[i] ?? '' });
    }
    onEdit(globalIdx, 'evidences', updated);
    setShowPopover(false);
  }, [editValues, evidences, field, globalIdx, onEdit]);

  // Close on outside click → auto-save
  useEffect(() => {
    if (!showPopover) return;
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        saveAndClose();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showPopover, saveAndClose]);

  const handleChange = (i: number, val: string) => {
    setEditValues(prev => {
      const next = [...prev];
      next[i] = val;
      return next;
    });
  };

  const handleRemove = (i: number) => {
    setEditValues(prev => prev.filter((_, idx) => idx !== i));
  };

  const handleAdd = () => {
    setEditValues(prev => [...prev, '']);
  };

  return (
    <div className="affiliation-cell">
      <div className="affiliation-text-row">
        <div className="evidence-items">
          {displayItems.length === 0 && <span className="bulk-chips-empty">—</span>}
          {displayItems.map((item, i) => (
            <div key={i} className="evidence-item">
              <span className="evidence-num">{i + 1}.</span>
              {isLink
                ? <a href={item} target="_blank" rel="noreferrer" className="bulk-evidence-link" title={item}>{item}</a>
                : <span className="bulk-evidence-text" title={item}>{item}</span>
              }
            </div>
          ))}
        </div>
        <div className="affiliation-actions" ref={popoverRef}>
          <button className="affiliation-edit-btn" onClick={openPopover} title="Edit" aria-label="Edit">✎</button>
          {showPopover && (
            <div className="evidence-edit-popover">
              {editValues.map((val, i) => (
                <div key={i} className="evidence-edit-row">
                  <span className="evidence-num">{i + 1}.</span>
                  <input
                    className="evidence-edit-input"
                    type={isLink ? 'url' : 'text'}
                    placeholder={isLink ? 'https://...' : 'Evidence description...'}
                    value={val}
                    onChange={e => handleChange(i, e.target.value)}
                    autoFocus={i === 0}
                  />
                  <button
                    className="affiliation-clear-btn"
                    onClick={() => handleRemove(i)}
                    title="Remove"
                    aria-label="Remove"
                  >
                    ×
                  </button>
                </div>
              ))}
              <div className="evidence-edit-actions">
                <button className="evidence-add-btn" onClick={handleAdd}>+ Add</button>
                <button className="evidence-save-btn" onClick={saveAndClose}>Done</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
