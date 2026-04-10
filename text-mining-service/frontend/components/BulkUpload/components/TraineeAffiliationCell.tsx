'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import type { RawInstitution } from '../types';
import { CLARISA_BASE_URL } from '../constants';

const CLARISA_INSTITUTIONS_URL = `${CLARISA_BASE_URL}/institutions`;

interface ClarisaInstitution {
  code: number;
  name: string;
  acronym?: string;
}

// Shares the same module-level cache as PartnersCell
let cachedInstitutions: ClarisaInstitution[] | null = null;
let fetchPromise: Promise<ClarisaInstitution[]> | null = null;

async function fetchInstitutions(): Promise<ClarisaInstitution[]> {
  if (cachedInstitutions) return cachedInstitutions;
  if (!fetchPromise) {
    fetchPromise = fetch(CLARISA_INSTITUTIONS_URL)
      .then(r => r.json() as Promise<ClarisaInstitution[]>)
      .then(data => {
        cachedInstitutions = data;
        return data;
      })
      .catch(err => {
        fetchPromise = null; // allow retry on next open
        throw err;
      });
  }
  return fetchPromise;
}

interface TraineeAffiliationCellProps {
  value: RawInstitution | null | undefined;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: RawInstitution | null) => void;
  disabled?: boolean;
}

export function TraineeAffiliationCell({ value, globalIdx, onEdit, disabled }: TraineeAffiliationCellProps) {
  const [showSearch, setShowSearch] = useState(false);
  const [query, setQuery] = useState('');
  const [allInstitutions, setAllInstitutions] = useState<ClarisaInstitution[]>(cachedInstitutions ?? []);
  const [loading, setLoading] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch institution list when popover first opens (not on mount — display name is stored in value)
  useEffect(() => {
    if (!showSearch || cachedInstitutions) return;
    setLoading(true);
    fetchInstitutions()
      .then(data => setAllInstitutions(data))
      .finally(() => setLoading(false));
  }, [showSearch]);

  // Close popover on outside click
  useEffect(() => {
    if (!showSearch) return;
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowSearch(false);
        setQuery('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSearch]);

  // Focus input when popover opens
  useEffect(() => {
    if (showSearch) inputRef.current?.focus();
  }, [showSearch]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return allInstitutions
      .filter(inst => inst.name.toLowerCase().includes(q))
      .slice(0, 50);
  }, [query, allInstitutions]);

  const handleSelect = useCallback((inst: ClarisaInstitution) => {
    onEdit(globalIdx, 'trainee_affiliation', {
      institution_name: inst.name,
      institution_id: String(inst.code),
      similarity_score: 100,
    });
    setShowSearch(false);
    setQuery('');
  }, [globalIdx, onEdit]);

  const handleClear = useCallback(() => {
    onEdit(globalIdx, 'trainee_affiliation', null);
  }, [globalIdx, onEdit]);

  const openSearch = useCallback(() => {
    setShowSearch(s => !s);
    setQuery('');
  }, []);

  const hasValue = value && value.institution_name;

  function affiliationDotClass(inst: RawInstitution): string {
    if (inst.institution_id !== null && inst.similarity_score >= 70) return 'affiliation-dot affiliation-dot-mapped';
    if (inst.institution_id !== null && inst.similarity_score < 70) return 'affiliation-dot affiliation-dot-low';
    return 'affiliation-dot affiliation-dot-unmapped';
  }

  return (
    <div className={`affiliation-cell${disabled ? ' cell-conditional-disabled' : ''}`}>
      <div className="affiliation-text-row">
        {hasValue && <span className={affiliationDotClass(value!)} title={`Score: ${value!.similarity_score}`} />}
        <span className="affiliation-name" title={hasValue ? `ID: ${value!.institution_id ?? '—'}` : undefined}>
          {hasValue ? value!.institution_name : <span className="bulk-chips-empty">—</span>}
        </span>
        <div className="affiliation-actions">
          <button
            className="affiliation-edit-btn"
            aria-label="Select institution"
            onClick={openSearch}
            title={hasValue ? 'Change institution' : 'Select institution'}
            disabled={disabled}
          >
            ✎
          </button>
          {hasValue && (
            <button
              className="affiliation-clear-btn"
              aria-label="Clear affiliation"
              onClick={handleClear}
              title="Clear"
              disabled={disabled}
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="partner-add-container" ref={popoverRef}>
        {showSearch && (
          <div className="partners-search-popover">
            <div className="partners-search-input-wrap">
              <input
                ref={inputRef}
                className="partners-search-input"
                placeholder={loading ? 'Loading...' : 'Search institution...'}
                value={query}
                onChange={e => setQuery(e.target.value)}
                disabled={loading}
              />
            </div>
            <ul className="partners-search-results">
              {query.trim() === '' && (
                <li className="partners-no-results">Type to search</li>
              )}
              {query.trim() !== '' && filtered.length === 0 && (
                <li className="partners-no-results">No institutions found</li>
              )}
              {filtered.map(inst => (
                <li
                  key={inst.code}
                  className="partners-search-result"
                  onClick={() => handleSelect(inst)}
                >
                  <span>{inst.name}</span>
                  {inst.acronym && (
                    <span className="partners-result-meta">{inst.acronym}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
