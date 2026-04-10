'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';

const LANGUAGES_URL = 'https://main-allianceindicatorstest.ciat.cgiar.org/api/tools/clarisa/languages';

interface StarLanguage {
  id: number;
  name: string;
  iso_alpha_2: string;
  iso_alpha_3: string;
  is_active: boolean;
}

interface RawLanguage {
  name: string;
  code: string;
}

// Module-level cache
let cachedLanguages: StarLanguage[] | null = null;
let fetchPromise: Promise<StarLanguage[]> | null = null;

async function fetchLanguages(token: string): Promise<StarLanguage[]> {
  if (cachedLanguages) return cachedLanguages;
  if (!fetchPromise) {
    fetchPromise = fetch(LANGUAGES_URL, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => {
        if (!r.ok) throw new Error(`Languages API error ${r.status}`);
        return r.json() as Promise<{ data?: StarLanguage[] }>;
      })
      .then(data => {
        cachedLanguages = (data.data ?? []).filter(l => l.is_active);
        return cachedLanguages;
      })
      .catch(err => {
        fetchPromise = null; // allow retry on next open
        throw err;
      });
  }
  return fetchPromise;
}

interface LanguageCellProps {
  value: RawLanguage | null | undefined;
  globalIdx: number;
  authToken: string | null;
  onEdit: (globalIdx: number, field: string, value: RawLanguage | null) => void;
  disabled?: boolean;
}

export function LanguageCell({ value, globalIdx, authToken, onEdit, disabled }: LanguageCellProps) {
  const [showSearch, setShowSearch] = useState(false);
  const [query, setQuery] = useState('');
  const [allLanguages, setAllLanguages] = useState<StarLanguage[]>(cachedLanguages ?? []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Pre-fetch on mount (when token is available) so display name resolves immediately
  useEffect(() => {
    if (cachedLanguages || !authToken) return;
    fetchLanguages(authToken)
      .then(data => setAllLanguages(data))
      .catch(() => { /* silently ignore pre-fetch failure; will retry on popover open */ });
  }, [authToken]);

  // Fetch when popover opens if not yet cached
  useEffect(() => {
    if (!showSearch || cachedLanguages) return;
    if (!authToken) { setError('No auth token available'); return; }
    setLoading(true);
    setError(null);
    fetchLanguages(authToken)
      .then(data => setAllLanguages(data))
      .catch(() => setError('Failed to load languages'))
      .finally(() => setLoading(false));
  }, [showSearch, authToken]);

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
    return allLanguages
      .filter(l => l.name?.toLowerCase().includes(q) || l.iso_alpha_2?.toLowerCase().includes(q) || l.iso_alpha_3?.toLowerCase().includes(q))
      .slice(0, 50);
  }, [query, allLanguages]);

  const handleSelect = useCallback((lang: StarLanguage) => {
    onEdit(globalIdx, 'language', { name: lang.name, code: lang.iso_alpha_3 });
    setShowSearch(false);
    setQuery('');
  }, [globalIdx, onEdit]);

  const handleClear = useCallback(() => {
    onEdit(globalIdx, 'language', null);
  }, [globalIdx, onEdit]);

  const openSearch = useCallback(() => {
    setShowSearch(s => !s);
    setQuery('');
  }, []);

  // Resolve display name from cache using iso_alpha_3 code; fall back to value.name if cache not yet loaded
  const displayName = useMemo(() => {
    if (!value?.code) return null;
    const found = (cachedLanguages ?? allLanguages).find(l => l.iso_alpha_3 === value.code);
    return found ? found.name : (value.name ?? value.code);
  }, [value, allLanguages]);

  return (
    <div className={`affiliation-cell${disabled ? ' cell-conditional-disabled' : ''}`}>
      <div className="affiliation-text-row">
        <span className="affiliation-name" title={value?.code ?? undefined}>
          {displayName ?? <span className="bulk-chips-empty">—</span>}
        </span>
        <div className="affiliation-actions">
          <button
            className="affiliation-edit-btn"
            aria-label="Select language"
            onClick={openSearch}
            title={displayName ? 'Change language' : 'Select language'}
            disabled={disabled}
          >
            ✎
          </button>
          {displayName && (
            <button
              className="affiliation-clear-btn"
              aria-label="Clear language"
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
                placeholder={loading ? 'Loading...' : error ? error : 'Search language...'}
                value={query}
                onChange={e => setQuery(e.target.value)}
                disabled={loading || !!error}
              />
            </div>
            <ul className="partners-search-results">
              {query.trim() === '' && !error && (
                <li className="partners-no-results">Type to search</li>
              )}
              {query.trim() !== '' && filtered.length === 0 && (
                <li className="partners-no-results">No languages found</li>
              )}
              {filtered.map(l => (
                <li
                  key={l.id}
                  className="partners-search-result"
                  onClick={() => handleSelect(l)}
                >
                  <span>{l.name}</span>
                  <span className="partners-result-meta">{l.iso_alpha_2}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
