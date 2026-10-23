'use client';

import { useMemo } from 'react';
import {
  PRIMARY_LEVER_ID_TO_NAME,
  PORTFOLIO_2026_MIN_YEAR,
  getPrimaryLeverOptions,
  parseResultYear,
} from '../constants';
import { CatalogMultiSelectCell } from './CatalogMultiSelectCell';

interface PrimaryLeversCellProps {
  values: number[];
  /** Result year — decides whether Primary Levers or Research Areas are offered. */
  year: unknown;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: number[]) => void;
  disabled?: boolean;
}

const labelFor = (id: number): string => PRIMARY_LEVER_ID_TO_NAME[id] ?? `Option ${id}`;

export function PrimaryLeversCell({ values, year, globalIdx, onEdit, disabled }: PrimaryLeversCellProps) {
  const parsedYear = parseResultYear(year);
  const options = useMemo(() => getPrimaryLeverOptions(year), [year]);
  const isResearchAreas = parsedYear !== null && parsedYear >= PORTFOLIO_2026_MIN_YEAR;

  return (
    <CatalogMultiSelectCell
      values={values}
      options={options}
      field="primary_levers"
      globalIdx={globalIdx}
      onEdit={onEdit}
      disabled={disabled}
      labelFor={labelFor}
      noun={isResearchAreas ? 'research area' : 'primary lever'}
      popoverTitle={`${isResearchAreas ? 'Research Areas' : 'Primary Levers'} · ${parsedYear}`}
      emptyHint="Set the Year first"
    />
  );
}
