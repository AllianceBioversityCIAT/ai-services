'use client';

import { useCallback, useEffect, useState } from 'react';
import { CLARISA_COUNTRIES_BFF_URL, CLARISA_INSTITUTION_TYPES_BFF_URL } from '../constants';
import type { ClarisaCountryOption, ClarisaInstitutionTypeOption } from '../types';

interface ClarisaCatalogsState {
  countries: ClarisaCountryOption[];
  institutionTypes: ClarisaInstitutionTypeOption[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

let cachedCountries: ClarisaCountryOption[] | null = null;
let cachedInstitutionTypes: ClarisaInstitutionTypeOption[] | null = null;
let countriesPromise: Promise<ClarisaCountryOption[]> | null = null;
let institutionTypesPromise: Promise<ClarisaInstitutionTypeOption[]> | null = null;

async function fetchCountriesCatalog(): Promise<ClarisaCountryOption[]> {
  if (cachedCountries) return cachedCountries;
  if (!countriesPromise) {
    countriesPromise = fetch(CLARISA_COUNTRIES_BFF_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Countries catalog error (${res.status})`);
        return res.json() as Promise<ClarisaCountryOption[]>;
      })
      .then((data) => {
        cachedCountries = [...data].sort((a, b) => a.name.localeCompare(b.name));
        return cachedCountries;
      })
      .catch((err) => {
        countriesPromise = null;
        throw err;
      });
  }
  return countriesPromise;
}

async function fetchInstitutionTypesCatalog(): Promise<ClarisaInstitutionTypeOption[]> {
  if (cachedInstitutionTypes) return cachedInstitutionTypes;
  if (!institutionTypesPromise) {
    institutionTypesPromise = fetch(CLARISA_INSTITUTION_TYPES_BFF_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Institution types catalog error (${res.status})`);
        return res.json() as Promise<ClarisaInstitutionTypeOption[]>;
      })
      .then((data) => {
        cachedInstitutionTypes = [...data].sort((a, b) => a.name.localeCompare(b.name));
        return cachedInstitutionTypes;
      })
      .catch((err) => {
        institutionTypesPromise = null;
        throw err;
      });
  }
  return institutionTypesPromise;
}

export function useClarisaCatalogs(enabled: boolean): ClarisaCatalogsState {
  const [countries, setCountries] = useState<ClarisaCountryOption[]>(cachedCountries ?? []);
  const [institutionTypes, setInstitutionTypes] = useState<ClarisaInstitutionTypeOption[]>(
    cachedInstitutionTypes ?? [],
  );
  const [loading, setLoading] = useState(enabled && (!cachedCountries || !cachedInstitutionTypes));
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => {
    cachedCountries = null;
    cachedInstitutionTypes = null;
    countriesPromise = null;
    institutionTypesPromise = null;
    setReloadToken((prev) => prev + 1);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([fetchCountriesCatalog(), fetchInstitutionTypesCatalog()])
      .then(([nextCountries, nextTypes]) => {
        if (cancelled) return;
        setCountries(nextCountries);
        setInstitutionTypes(nextTypes);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message || 'Could not load CLARISA catalogs');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, reloadToken]);

  return { countries, institutionTypes, loading, error, reload };
}
