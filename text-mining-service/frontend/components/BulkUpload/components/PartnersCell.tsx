'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import type { RawInstitution } from '../types';

const CLARISA_INSTITUTIONS_URL = 'https://clarisatest-back.ciat.cgiar.org/api/institutions';

interface ClarisaCountryOffice {
  name: string;
  isHeadquarter: number;
}

interface ClarisaInstitution {
  code: number;
  name: string;
  acronym?: string;
  countryOfficeDTO?: ClarisaCountryOffice[];
}

// Module-level cache — fetched once for the whole session
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

interface PartnersCellProps {
  partners: RawInstitution[];
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: RawInstitution[]) => void;
  field?: string;
}

function chipClass(p: RawInstitution): string {
  if (p.institution_id !== null && p.similarity_score >= 70) return 'partner-chip partner-chip-mapped';
  if (p.institution_id !== null && p.similarity_score < 70) return 'partner-chip partner-chip-low';
  return 'partner-chip partner-chip-unmapped';
}

function isRemovable(_p: RawInstitution): boolean {
  return true;
}

export function PartnersCell({ partners, globalIdx, onEdit, field = 'partners' }: PartnersCellProps) {
  const [showSearch, setShowSearch] = useState(false);
  const [query, setQuery] = useState('');
  const [allInstitutions, setAllInstitutions] = useState<ClarisaInstitution[]>(cachedInstitutions ?? []);
  const [loading, setLoading] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch institution list when popover first opens
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

  // Client-side filtering
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return allInstitutions
      .filter(inst => inst.name.toLowerCase().includes(q))
      .slice(0, 50);
  }, [query, allInstitutions]);

  const handleRemove = useCallback((idx: number) => {
    onEdit(globalIdx, field, partners.filter((_, i) => i !== idx));
  }, [partners, globalIdx, onEdit, field]);

  const handleAdd = useCallback((inst: ClarisaInstitution) => {
    const already = partners.some(p => p.institution_id === String(inst.code));
    if (!already) {
      const newPartner: RawInstitution = {
        institution_name: inst.name,
        institution_id: String(inst.code),
        similarity_score: 100,
      };
      onEdit(globalIdx, field, [...partners, newPartner]);
    }
    setShowSearch(false);
    setQuery('');
  }, [partners, globalIdx, onEdit, field]);

  return (
    <div className="partners-cell">
      <div className="partners-chips">
        {partners.length === 0 && <span className="bulk-chips-empty">—</span>}
        {partners.map((p, i) => (
          <span key={i} className={chipClass(p)} title={p.institution_name}>
            <span className="partner-chip-label">{p.institution_name}</span>
            {isRemovable(p) && (
              <button
                className="partner-chip-remove"
                aria-label={`Remove ${p.institution_name}`}
                onClick={() => handleRemove(i)}
              >
                ×
              </button>
            )}
          </span>
        ))}
      </div>

      <div className="partner-add-container" ref={popoverRef}>
        <button
          className="partner-add-btn"
          aria-label="Add partner institution"
          onClick={() => setShowSearch(s => !s)}
        >
          +
        </button>

        {showSearch && (
          <div className="partners-search-popover">
            <input
              ref={inputRef}
              className="partners-search-input"
              placeholder="Search institution…"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            {loading && <div className="partners-search-loading">Loading…</div>}
            {!loading && filtered.length > 0 && (
              <ul className="partners-search-results">
                {filtered.map(inst => {
                  const hq = inst.countryOfficeDTO?.find(c => c.isHeadquarter === 1) ?? inst.countryOfficeDTO?.[0];
                  return (
                    <li
                      key={inst.code}
                      className="partners-search-result"
                      onClick={() => handleAdd(inst)}
                    >
                      {inst.acronym && <strong className="partners-result-acronym">{inst.acronym}</strong>}
                      {inst.acronym && <span className="partners-result-sep"> - </span>}
                      <span className="partners-result-name">{inst.name}</span>
                      {hq && <span className="partners-result-country"> - {hq.name}</span>}
                    </li>
                  );
                })}
              </ul>
            )}
            {!loading && query.trim() && filtered.length === 0 && (
              <div className="partners-search-empty">No results</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
