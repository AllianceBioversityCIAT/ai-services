'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type { RawCountry } from '../types';

const CLARISA_COUNTRIES_URL = 'https://clarisatest-back.ciat.cgiar.org/api/countries';

interface ClarisaCountry {
  isoAlpha2: string;
  name: string;
}

// Module-level cache
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

interface CountriesCellProps {
  values: RawCountry[];
  geoscopeLevel: string | undefined;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: RawCountry[]) => void;
}

const AREA_PATTERN = /^[A-Z]{2}-[A-Z0-9]{1,3}$/i;

export function CountriesCell({ values, geoscopeLevel, globalIdx, onEdit }: CountriesCellProps) {
  const [countries, setCountries] = useState<ClarisaCountry[]>([]);
  const [showPopover, setShowPopover] = useState(false);
  const [search, setSearch] = useState('');
  const [areaInputs, setAreaInputs] = useState<Record<string, string>>({});
  const popoverRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const isSubnational = geoscopeLevel === 'Sub-national';

  useEffect(() => {
    if (!showPopover) return;
    fetchCountries().then(setCountries);
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

  const getName = useCallback((code: string): string => {
    return countries.find(c => c.isoAlpha2 === code)?.name ?? code;
  }, [countries]);

  const handleRemoveCountry = useCallback((code: string) => {
    onEdit(globalIdx, 'countries', values.filter(v => v.code !== code));
  }, [values, globalIdx, onEdit]);

  const handleAddCountry = useCallback((country: ClarisaCountry) => {
    if (!values.find(v => v.code === country.isoAlpha2)) {
      onEdit(globalIdx, 'countries', [...values, { code: country.isoAlpha2 }]);
    }
    setShowPopover(false);
  }, [values, globalIdx, onEdit]);

  const handleAddArea = useCallback((countryCode: string) => {
    const raw = (areaInputs[countryCode] ?? '').trim().toUpperCase();
    if (!raw || !AREA_PATTERN.test(raw)) return;
    const updated = values.map(v => {
      if (v.code !== countryCode) return v;
      const areas = v.areas ?? [];
      if (areas.includes(raw)) return v;
      return { ...v, areas: [...areas, raw] };
    });
    onEdit(globalIdx, 'countries', updated);
    setAreaInputs(prev => ({ ...prev, [countryCode]: '' }));
  }, [values, globalIdx, onEdit, areaInputs]);

  const handleRemoveArea = useCallback((countryCode: string, area: string) => {
    const updated = values.map(v => {
      if (v.code !== countryCode) return v;
      return { ...v, areas: (v.areas ?? []).filter(a => a !== area) };
    });
    onEdit(globalIdx, 'countries', updated);
  }, [values, globalIdx, onEdit]);

  const filtered = countries
    .filter(c => !values.find(v => v.code === c.isoAlpha2))
    .filter(c => c.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="geo-cell">
      {values.length === 0 && <span className="bulk-chips-empty">—</span>}
      {values.map(country => (
        <div key={country.code} className="geo-country-block">
          {/* Country chip */}
          <div className="geo-country-header">
            <span className="bulk-chip geo-chip" title={getName(country.code)}>
              <span className="bulk-chip-label">{getName(country.code)}</span>
              <button
                className="partner-chip-remove"
                aria-label={`Remove ${country.code}`}
                onClick={() => handleRemoveCountry(country.code)}
              >
                ×
              </button>
            </span>
          </div>

          {/* Area chips (sub-national only) */}
          {isSubnational && (
            <div className="geo-areas">
              {(country.areas ?? []).map(area => {
                const valid = AREA_PATTERN.test(area);
                return (
                  <span key={area} className={`bulk-chip geo-area-chip${!valid ? ' geo-area-invalid' : ''}`}>
                    {area}
                    <button
                      className="partner-chip-remove"
                      aria-label={`Remove area ${area}`}
                      onClick={() => handleRemoveArea(country.code, area)}
                    >
                      ×
                    </button>
                  </span>
                );
              })}
              <div className="geo-area-input-row">
                <input
                  type="text"
                  className="geo-area-input"
                  placeholder="e.g. CO-CUN"
                  value={areaInputs[country.code] ?? ''}
                  onChange={e => setAreaInputs(prev => ({ ...prev, [country.code]: e.target.value }))}
                  onKeyDown={e => { if (e.key === 'Enter') handleAddArea(country.code); }}
                />
                <button
                  className="geo-area-add-btn"
                  onClick={() => handleAddArea(country.code)}
                >
                  +
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Add country popover */}
      <div className="partner-add-container" ref={popoverRef}>
        <button
          className="partner-add-btn"
          aria-label="Add country"
          onClick={() => setShowPopover(s => !s)}
        >
          +
        </button>
        {showPopover && (
          <div className="partners-search-popover">
            <div className="partners-search-input-wrap">
              <input
                ref={searchRef}
                className="partners-search-input"
                placeholder="Search country..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <ul className="partners-search-results">
              {filtered.length === 0 && (
                <li className="partners-no-results">No countries found</li>
              )}
              {filtered.map(c => (
                <li
                  key={c.isoAlpha2}
                  className="partners-search-result"
                  onClick={() => handleAddCountry(c)}
                >
                  <span className="partners-result-name">{c.name}</span>
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
