'use client';

import { useMemo } from 'react';
import {
  PORTFOLIO_2026_MIN_YEAR,
  STRATEGIC_OBJECTIVE_ID_TO_NAME,
  getStrategicObjectiveOptions,
  parseResultYear,
} from '../constants';
import { CatalogMultiSelectCell } from './CatalogMultiSelectCell';

interface StrategicObjectivesCellProps {
  values: number[];
  /** Result year — the field only applies from 2026 onwards. */
  year: unknown;
  globalIdx: number;
  onEdit: (globalIdx: number, field: string, value: number[]) => void;
  disabled?: boolean;
}

const labelFor = (id: number): string => STRATEGIC_OBJECTIVE_ID_TO_NAME[id] ?? `Objective ${id}`;

export function StrategicObjectivesCell({ values, year, globalIdx, onEdit, disabled }: StrategicObjectivesCellProps) {
  const parsedYear = parseResultYear(year);
  const options = useMemo(() => getStrategicObjectiveOptions(year), [year]);

  // Distinguish "cannot know yet" from "genuinely does not apply"
  const emptyHint = parsedYear === null
    ? 'Set the Year first'
    : `Not applicable before ${PORTFOLIO_2026_MIN_YEAR}`;

  return (
    <CatalogMultiSelectCell
      values={values}
      options={options}
      field="strategic_objectives"
      globalIdx={globalIdx}
      onEdit={onEdit}
      disabled={disabled}
      labelFor={labelFor}
      noun="strategic objective"
      popoverTitle={`Strategic Objectives · ${parsedYear}`}
      emptyHint={emptyHint}
    />
  );
}
