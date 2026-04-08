'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

const CLARISA_REGIONS_URL = 'https://clarisatest-back.ciat.cgiar.org/api/regions/un-regions';

interface ClarisaRegion {
  um49Code: number;
  name: string;
}

// Module-level cache
let cachedRegions: ClarisaRegion[] | null = null;
let fetchPromise: Promise<ClarisaRegion[]> | null = null;

async function fetchRegions(): Promise<ClarisaRegion[]> {
  if (cachedRegions) return cachedRegions;
  if (!fetchPromise) {
    fetchPromise = fetch(CLARISA_REGIONS_URL)
      .then(r => r.json() as Promise<ClarisaRegion[]>)
      .then(data => {
        cachedRegions = data;
        return data;
      });
  }
  return fetchPromise;
}

interface RegionsCellProps {
  values: number[];
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: number[]) => void;
}

export function RegionsCell({ values, globalIdx, onEdit }: RegionsCellProps) {
  const [regions, setRegions] = useState<ClarisaRegion[]>([]);
  const [showPopover, setShowPopover] = useState(false);
  const [search, setSearch] = useState('');
  const popoverRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Pre-fetch on mount so chip labels are available without opening the popover
  useEffect(() => {
    fetchRegions().then(setRegions);
  }, []);

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

  const getLabel = useCallback((code: number): string => {
    return regions.find(r => r.um49Code === code)?.name ?? `Region ${code}`;
  }, [regions]);

  const handleRemove = useCallback((code: number) => {
    onEdit(globalIdx, 'regions', values.filter(v => v !== code));
  }, [values, globalIdx, onEdit]);

  const handleAdd = useCallback((region: ClarisaRegion) => {
    if (!values.includes(region.um49Code)) {
      onEdit(globalIdx, 'regions', [...values, region.um49Code]);
    }
    setShowPopover(false);
  }, [values, globalIdx, onEdit]);

  const filtered = regions
    .filter(r => !values.includes(r.um49Code))
    .filter(r => r.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="geo-cell">
      <div className="bulk-chips">
        {values.length === 0 && <span className="bulk-chips-empty">—</span>}
        {values.map(code => (
          <span key={code} className="bulk-chip geo-chip" title={getLabel(code)}>
            <span className="bulk-chip-label">{getLabel(code)}</span>
            <button
              className="partner-chip-remove"
              aria-label={`Remove region ${code}`}
              onClick={() => handleRemove(code)}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      <div className="partner-add-container" ref={popoverRef}>
        <button
          className="partner-add-btn"
          aria-label="Add region"
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
                placeholder="Search region..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <ul className="partners-search-results">
              {filtered.length === 0 && (
                <li className="partners-no-results">No regions found</li>
              )}
              {filtered.map(r => (
                <li
                  key={r.um49Code}
                  className="partners-search-result"
                  onClick={() => handleAdd(r)}
                >
                  <span className="partners-result-name">{r.name}</span>
                  <span className="partners-result-meta">UN M.49: {r.um49Code}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
