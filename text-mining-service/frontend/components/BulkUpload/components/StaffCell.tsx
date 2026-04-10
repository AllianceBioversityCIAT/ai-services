'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

const STAFF_URL = 'https://main-allianceindicatorstest.ciat.cgiar.org/api/agresso/staff';

interface StaffPerson {
  carnet: string;
  first_name: string;
  last_name: string;
  email: string;
  is_active: boolean;
  status: string;
  center: string;
}

export interface RawStaff {
  name: string;
  code: string;
  similarity_score: number;
}

interface StaffCellProps {
  value: RawStaff | null | undefined;
  globalIdx: number;
  field: string;
  authToken: string | null;
  onEdit: (globalIdx: number, field: string, value: RawStaff | null) => void;
  disabled?: boolean;
}

export function StaffCell({ value, globalIdx, field, authToken, onEdit, disabled }: StaffCellProps) {
  const [showSearch, setShowSearch] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StaffPerson[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hasValue = value != null && Boolean(value.name);

  function staffDotClass(v: RawStaff): string {
    if (v.similarity_score >= 70) return 'affiliation-dot affiliation-dot-mapped';
    if (v.similarity_score > 0) return 'affiliation-dot affiliation-dot-low';
    return 'affiliation-dot affiliation-dot-unmapped';
  }

  // Debounced server-side search
  useEffect(() => {
    if (!showSearch) return;
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      if (!authToken) { setError('No auth token'); return; }
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${STAFF_URL}?search=${encodeURIComponent(q)}`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });
        if (!res.ok) throw new Error(`Staff API error ${res.status}`);
        const data = await res.json() as { data?: StaffPerson[] };
        setResults((data.data ?? []).filter(p => p.is_active !== false));
      } catch {
        setError('Failed to load staff');
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, showSearch, authToken]);

  // Close on outside click
  useEffect(() => {
    if (!showSearch) return;
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowSearch(false);
        setQuery('');
        setResults([]);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSearch]);

  useEffect(() => {
    if (showSearch) inputRef.current?.focus();
  }, [showSearch]);

  const handleSelect = useCallback((person: StaffPerson) => {
    onEdit(globalIdx, field, {
      name: `${person.first_name} ${person.last_name}`,
      code: person.carnet,
      similarity_score: 100,
    });
    setShowSearch(false);
    setQuery('');
    setResults([]);
  }, [globalIdx, field, onEdit]);

  const handleClear = useCallback(() => {
    onEdit(globalIdx, field, null);
  }, [globalIdx, field, onEdit]);

  const openSearch = useCallback(() => {
    setShowSearch(s => !s);
    setQuery('');
    setResults([]);
  }, []);

  return (
    <div className={`affiliation-cell${disabled ? ' cell-conditional-disabled' : ''}`}>
      <div className="affiliation-text-row">
        {hasValue && <span className={staffDotClass(value!)} title={`Score: ${value!.similarity_score}`} />}
        <span className="affiliation-name">
          {hasValue ? value!.name : <span className="bulk-chips-empty">—</span>}
        </span>
        <div className="affiliation-actions" ref={popoverRef}>
          <button
            className="affiliation-edit-btn"
            aria-label="Select person"
            onClick={openSearch}
            title={hasValue ? 'Change person' : 'Select person'}
            disabled={disabled}
          >
            ✎
          </button>
          {hasValue && (
            <button
              className="affiliation-clear-btn"
              aria-label="Clear"
              onClick={handleClear}
              title="Clear"
              disabled={disabled}
            >
              ×
            </button>
          )}
          {showSearch && (
            <div className="partners-search-popover">
              <div className="partners-search-input-wrap">
                <input
                  ref={inputRef}
                  className="partners-search-input"
                  placeholder={loading ? 'Searching...' : 'Type name or email (min. 2 chars)...'}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                />
              </div>
              <ul className="partners-search-results">
                {query.trim().length < 2 && (
                  <li className="partners-no-results">Type at least 2 characters</li>
                )}
                {query.trim().length >= 2 && loading && (
                  <li className="partners-no-results">Searching...</li>
                )}
                {query.trim().length >= 2 && !loading && error && (
                  <li className="partners-no-results">{error}</li>
                )}
                {query.trim().length >= 2 && !loading && !error && results.length === 0 && (
                  <li className="partners-no-results">No staff found</li>
                )}
                {results.map(person => (
                  <li
                    key={person.carnet}
                    className="partners-search-result staff-search-result"
                    onClick={() => handleSelect(person)}
                  >
                    <span className="staff-result-name">{person.first_name} {person.last_name}</span>
                    <span className="staff-result-email">{person.email}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
