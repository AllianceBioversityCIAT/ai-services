'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';

const CLARISA_COUNTRIES_URL = 'https://clarisatest-back.ciat.cgiar.org/api/countries';

interface ClarisaCountry {
  isoAlpha2: string;
  name: string;
}

// Module-level cache — shared with CountriesCell
let cachedCountries: ClarisaCountry[] | null = null;
let fetchPromise: Promise<ClarisaCountry[]> | null = null;

async function fetchCountries(): Promise<ClarisaCountry[]> {
  if (cachedCountries) return cachedCountries;
  if (!fetchPromise) {
    fetchPromise = fetch(CLARISA_COUNTRIES_URL)
      .then(r => r.json() as Promise<ClarisaCountry[]>)
      .then(data => {
        cachedCountries = data;
        return data;
      });
  }
  return fetchPromise;
}

interface TraineeNationalityCellProps {
  value: { code: string } | null | undefined;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: { code: string } | null) => void;
  disabled?: boolean;
}

export function TraineeNationalityCell({ value, globalIdx, onEdit, disabled }: TraineeNationalityCellProps) {
  const [showSearch, setShowSearch] = useState(false);
  const [query, setQuery] = useState('');
  const [allCountries, setAllCountries] = useState<ClarisaCountry[]>(cachedCountries ?? []);
  const [loading, setLoading] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch only when popover opens — display name resolved from value.code at render time
  useEffect(() => {
    if (!showSearch || cachedCountries) return;
    setLoading(true);
    fetchCountries()
      .then(data => setAllCountries(data))
      .finally(() => setLoading(false));
  }, [showSearch]);

  // Close on outside click
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

  useEffect(() => {
    if (showSearch) inputRef.current?.focus();
  }, [showSearch]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return allCountries
      .filter(c => c.name.toLowerCase().includes(q) || c.isoAlpha2.toLowerCase().includes(q))
      .slice(0, 50);
  }, [query, allCountries]);

  // Resolve display name from cached list; fall back to code if not yet loaded
  const displayName = useMemo(() => {
    if (!value?.code) return null;
    const found = (cachedCountries ?? allCountries).find(c => c.isoAlpha2 === value.code);
    return found ? found.name : value.code;
  }, [value, allCountries]);

  const handleSelect = useCallback((country: ClarisaCountry) => {
    onEdit(globalIdx, 'trainee_nationality', { code: country.isoAlpha2 });
    setShowSearch(false);
    setQuery('');
  }, [globalIdx, onEdit]);

  const handleClear = useCallback(() => {
    onEdit(globalIdx, 'trainee_nationality', null);
  }, [globalIdx, onEdit]);

  const openSearch = useCallback(() => {
    setShowSearch(s => !s);
    setQuery('');
  }, []);

  return (
    <div className={`affiliation-cell${disabled ? ' cell-conditional-disabled' : ''}`}>
      <div className="affiliation-text-row">
        <span className="affiliation-name" title={value?.code ?? undefined}>
          {displayName ?? <span className="bulk-chips-empty">—</span>}
        </span>
        <div className="affiliation-actions">
          <button
            className="affiliation-edit-btn"
            aria-label="Select country"
            onClick={openSearch}
            disabled={disabled}
            title={displayName ? 'Change country' : 'Select country'}
          >
            ✎
          </button>
          {displayName && (
            <button
              className="affiliation-clear-btn"
              aria-label="Clear nationality"
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
                placeholder={loading ? 'Loading...' : 'Search country...'}
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
                <li className="partners-no-results">No countries found</li>
              )}
              {filtered.map(c => (
                <li
                  key={c.isoAlpha2}
                  className="partners-search-result"
                  onClick={() => handleSelect(c)}
                >
                  <span>{c.name}</span>
                  <span className="partners-result-meta">{c.isoAlpha2}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
