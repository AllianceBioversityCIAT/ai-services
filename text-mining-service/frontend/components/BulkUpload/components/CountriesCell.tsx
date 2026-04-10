'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type { RawCountry } from '../types';
import { STAR_BASE_URL, CLARISA_BASE_URL } from '../constants';

const CLARISA_COUNTRIES_URL = `${CLARISA_BASE_URL}/countries`;
const SUBNATIONAL_URL = (iso: string) =>
  `${STAR_BASE_URL}/tools/clarisa/sub-nationals/country/${iso}`;

interface ClarisaCountry {
  isoAlpha2: string;
  name: string;
}

interface SubNationalArea {
  id: number;
  code: string;
  name: string;
  country_iso_alpha_2: string;
  is_active: boolean;
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
      })
      .catch(err => {
        fetchPromise = null;
        throw err;
      });
  }
  return fetchPromise;
}

// Per-country sub-national cache
const subNationalCache = new Map<string, SubNationalArea[]>();
const subNationalFetchPromises = new Map<string, Promise<SubNationalArea[]>>();

async function fetchSubNationals(iso: string, token: string): Promise<SubNationalArea[]> {
  if (subNationalCache.has(iso)) return subNationalCache.get(iso)!;
  if (!subNationalFetchPromises.has(iso)) {
    const promise = fetch(SUBNATIONAL_URL(iso), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => {
        if (!r.ok) throw new Error(`Sub-nationals API error ${r.status}`);
        return r.json() as Promise<{ data?: SubNationalArea[] }>;
      })
      .then(data => {
        const areas = (data.data ?? []).filter(a => a.is_active !== false);
        subNationalCache.set(iso, areas);
        subNationalFetchPromises.delete(iso);
        return areas;
      })
      .catch(err => {
        subNationalFetchPromises.delete(iso);
        throw err;
      });
    subNationalFetchPromises.set(iso, promise);
  }
  return subNationalFetchPromises.get(iso)!;
}

interface CountriesCellProps {
  values: RawCountry[];
  geoscopeLevel: string | undefined;
  globalIdx: number;
  authToken: string | null;
  onEdit: (globalIdx: number, field: string, value: RawCountry[]) => void;
}

export function CountriesCell({ values, geoscopeLevel, globalIdx, authToken, onEdit }: CountriesCellProps) {
  const [countries, setCountries] = useState<ClarisaCountry[]>([]);
  const [showPopover, setShowPopover] = useState(false);
  const [search, setSearch] = useState('');
  // areaPopover: which country code has the area picker open
  const [areaPopover, setAreaPopover] = useState<string | null>(null);
  const [areaSearch, setAreaSearch] = useState('');
  const [subNationals, setSubNationals] = useState<SubNationalArea[]>([]);
  const [areaLoading, setAreaLoading] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const areaPopoverRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const areaSearchRef = useRef<HTMLInputElement>(null);

  const isSubnational = geoscopeLevel === 'Sub-national';

  useEffect(() => {
    if (!showPopover) return;
    fetchCountries().then(setCountries);
    setSearch('');
    setTimeout(() => searchRef.current?.focus(), 50);
  }, [showPopover]);

  // Fetch sub-nationals when area popover opens
  useEffect(() => {
    if (!areaPopover || !authToken) return;
    setAreaSearch('');
    setAreaLoading(true);
    fetchSubNationals(areaPopover, authToken)
      .then(setSubNationals)
      .catch(() => setSubNationals([]))
      .finally(() => setAreaLoading(false));
    setTimeout(() => areaSearchRef.current?.focus(), 50);
  }, [areaPopover, authToken]);

  // Close country popover on outside click
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

  // Close area popover on outside click
  useEffect(() => {
    if (!areaPopover) return;
    function handleClickOutside(e: MouseEvent) {
      if (areaPopoverRef.current && !areaPopoverRef.current.contains(e.target as Node)) {
        setAreaPopover(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [areaPopover]);

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

  const handleAddArea = useCallback((countryCode: string, area: SubNationalArea) => {
    const updated = values.map(v => {
      if (v.code !== countryCode) return v;
      const areas = v.areas ?? [];
      if (areas.includes(area.code)) return v;
      return { ...v, areas: [...areas, area.code] };
    });
    onEdit(globalIdx, 'countries', updated);
    setAreaPopover(null);
  }, [values, globalIdx, onEdit]);

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

  const filteredAreas = subNationals.filter(a => {
    const q = areaSearch.toLowerCase();
    return a.name.toLowerCase().includes(q) || a.code.toLowerCase().includes(q);
  });

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
              {(country.areas ?? []).map(area => (
                <span key={area} className="bulk-chip geo-area-chip">
                  {area}
                  <button
                    className="partner-chip-remove"
                    aria-label={`Remove area ${area}`}
                    onClick={() => handleRemoveArea(country.code, area)}
                  >
                    ×
                  </button>
                </span>
              ))}
              {/* Area add popover */}
              <div className="partner-add-container" ref={areaPopover === country.code ? areaPopoverRef : undefined}>
                <button
                  className="partner-add-btn"
                  aria-label="Add area"
                  onClick={() => setAreaPopover(p => p === country.code ? null : country.code)}
                >
                  +
                </button>
                {areaPopover === country.code && (
                  <div className="partners-search-popover">
                    <div className="partners-search-input-wrap">
                      <input
                        ref={areaSearchRef}
                        className="partners-search-input"
                        placeholder={areaLoading ? 'Loading...' : 'Search area...'}
                        value={areaSearch}
                        onChange={e => setAreaSearch(e.target.value)}
                        disabled={areaLoading}
                      />
                    </div>
                    <ul className="partners-search-results">
                      {areaLoading && <li className="partners-no-results">Loading...</li>}
                      {!areaLoading && filteredAreas.length === 0 && (
                        <li className="partners-no-results">No areas found</li>
                      )}
                      {!areaLoading && filteredAreas.map(area => (
                        <li
                          key={area.id}
                          className="partners-search-result"
                          onClick={() => handleAddArea(country.code, area)}
                        >
                          <span className="partners-result-name">{area.name}</span>
                          <span className="partners-result-meta">{area.code}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
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

