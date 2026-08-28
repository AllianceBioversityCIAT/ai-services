import type { BulkUploadResult, ColumnDef, RawInstitution, RawUser, RawLanguage, RawCountry, RawEvidence, RecordStatus, TabType, SortDirection, TableSortConfig } from '../types';
import { NUMERIC_FIELDS, PRIMARY_LEVER_ID_TO_NAME, STRATEGIC_OBJECTIVE_ID_TO_NAME, RESULTS_TABLE_COLUMNS } from '../constants';
import { checkCompleteness } from './completenessChecker';

const NON_SORTABLE_COLUMN_TYPES = new Set<ColumnDef['type']>(['checkbox', 'status', 'link']);

/** Column header label for the active tab (e.g. Completeness vs STAR Status). */
export function getColumnLabel(col: ColumnDef, tab: TabType): string {
  if (tab === 'submitted' && col.submittedLabel) return col.submittedLabel;
  return col.label;
}

const ASSET_IP_OWNER_ID_TO_NAME: Record<number, string> = {
  1: 'International Center for Tropical Agriculture - CIAT',
  2: 'Bioversity International',
  3: 'Bioversity International and International Center for Tropical Agriculture - CIAT',
  4: 'Others',
};

/**
 * Normalises a stored catalog selection to a list of numeric ids.
 * Accepts an array of numbers, an array of {id} objects, or a JSON string.
 */
export function parseIdList(raw: unknown): number[] {
  const arr: unknown[] = Array.isArray(raw)
    ? raw
    : typeof raw === 'string' && raw.trim().startsWith('[')
      ? (() => { try { return JSON.parse(raw) as unknown[]; } catch { return []; } })()
      : [];
  return arr
    .map((v) => (typeof v === 'object' && v !== null && 'id' in v ? Number((v as { id: unknown }).id) : Number(v)))
    .filter((n) => Number.isFinite(n));
}

/** Reads a deep path like "a.b.c" from an object. */
export function getNestedValue(obj: BulkUploadResult, path: string): unknown {
  if (!path.includes('.')) return obj[path];
  const parts = path.split('.');
  let current: unknown = obj;
  for (const part of parts) {
    if (current !== null && typeof current === 'object' && part in (current as Record<string, unknown>)) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return current;
}

/** Sets a deep path like "a.b.c" on an object (mutates). */
export function setNestedValue(obj: BulkUploadResult, path: string, value: unknown): void {
  if (!path.includes('.')) {
    obj[path] = value;
    return;
  }
  const parts = path.split('.');
  let current: Record<string, unknown> = obj as Record<string, unknown>;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (!current[part] || typeof current[part] !== 'object') {
      current[part] = {};
    }
    current = current[part] as Record<string, unknown>;
  }
  current[parts[parts.length - 1]] = value;
}

/**
 * Returns an array of human-readable filter tokens for a single cell.
 * Arrays are expanded so each element becomes an individual filter option.
 */
export function getFilterTokens(columnKey: string, value: unknown): string[] {
  if (value === null || value === undefined) return ['(Empty)'];

  // Institution arrays: partners, trainees_description
  if (columnKey === 'partners' || columnKey === 'trainees_description') {
    const arr = value as RawInstitution[];
    if (!Array.isArray(arr) || arr.length === 0) return ['(Empty)'];
    const mapped = arr.filter(i => i.institution_id !== null && i.institution_id !== undefined && i.similarity_score >= 70);
    if (mapped.length === 0) return ['(Empty)'];
    return mapped.map(i => i.mapped_institution_name ?? i.institution_name ?? '(Empty)');
  }

  // Single institution: trainee_affiliation
  if (columnKey === 'trainee_affiliation') {
    const inst = value as RawInstitution;
    if (inst.institution_id === null || inst.institution_id === undefined || inst.similarity_score < 70) return ['(Empty)'];
    return [inst.mapped_institution_name ?? inst.institution_name ?? '(Empty)'];
  }

  // Staff (RawUser): main_contact_person, training_supervisor
  if (columnKey === 'main_contact_person' || columnKey === 'training_supervisor') {
    const user = value as RawUser;
    if (!user.code || user.similarity_score < 70) return ['(Empty)'];
    return [user.mapped_name ?? user.name ?? '(Empty)'];
  }

  // Language
  if (columnKey === 'language') {
    const lang = value as RawLanguage;
    return [lang.name ?? lang.code ?? '(Empty)'];
  }

  // Trainee nationality
  if (columnKey === 'trainee_nationality') {
    const country = value as RawCountry;
    return [country.code ?? '(Empty)'];
  }

  // Countries array
  if (columnKey === 'countries') {
    const arr = value as RawCountry[];
    if (!Array.isArray(arr) || arr.length === 0) return ['(Empty)'];
    return arr.map(c => c.code ?? '(Empty)');
  }

  // Regions array (number[])
  if (columnKey === 'regions') {
    const arr = value as number[];
    if (!Array.isArray(arr) || arr.length === 0) return ['(Empty)'];
    return arr.map(r => String(r));
  }

  // Primary Levers / Research Areas (number[] of catalog ids)
  if (columnKey === 'primary_levers') {
    const arr = value as number[];
    if (!Array.isArray(arr) || arr.length === 0) return ['(Empty)'];
    return arr.map(id => PRIMARY_LEVER_ID_TO_NAME[Number(id)] ?? String(id));
  }

  // Strategic Objectives (number[] of catalog ids)
  if (columnKey === 'strategic_objectives') {
    const arr = value as number[];
    if (!Array.isArray(arr) || arr.length === 0) return ['(Empty)'];
    return arr.map(id => STRATEGIC_OBJECTIVE_ID_TO_NAME[Number(id)] ?? String(id));
  }

  // String arrays: keywords
  if (Array.isArray(value)) {
    if (value.length === 0) return ['(Empty)'];
    return (value as unknown[]).map(v => String(v));
  }

  // Evidences — too complex to filter meaningfully; skip
  if (columnKey === 'evidences') {
    const arr = value as RawEvidence[];
    if (!Array.isArray(arr) || arr.length === 0) return ['(Empty)'];
    return arr.map(e => e.evidence_link || e.evidence_description || '(Empty)');
  }

  // Asset IP owner (stored as number or string)
  if (columnKey === 'asset_ip_owner_id') {
    const name = ASSET_IP_OWNER_ID_TO_NAME[Number(value)];
    return [name ?? String(value)];
  }

  // Primitives
  return [String(value)];
}

/** Returns filter tokens for a column, including computed columns like completeness. */
export function getColumnFilterTokens(
  columnKey: string,
  result: BulkUploadResult,
  recordStatus?: RecordStatus,
  tab: TabType = 'pending',
): string[] {
  if (columnKey === 'completeness') {
    if (tab === 'submitted') {
      const subType = recordStatus?.submissionType;
      if (subType === 'approved') return ['✓ Approved'];
      if (subType === 'draft') return ['Draft'];
      return ['Submitted'];
    }
    const { isComplete } = checkCompleteness(result);
    return [isComplete ? '✓ Complete' : '⚠ Incomplete'];
  }

  return getFilterTokens(columnKey, getNestedValue(result, columnKey));
}

/** Returns sorted unique human-readable filter values for a column across all rows. */
export function getUniqueValues(
  results: BulkUploadResult[],
  columnKey: string,
  recordStatuses?: Record<string, RecordStatus>,
  tab: TabType = 'pending',
): string[] {
  const values = new Set<string>();
  for (const result of results) {
    const recordStatus = recordStatuses?.[String(result.id)];
    const tokens = getColumnFilterTokens(columnKey, result, recordStatus, tab);
    tokens.forEach(t => values.add(t));
  }
  return Array.from(values).sort();
}

/** @deprecated Use getFilterTokens for column-aware formatting */
export function formatCellValueForFilter(value: unknown): string {
  if (value === null || value === undefined) return '(Empty)';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/** Simplifies an S3 full path to a readable label (filename only). */
export function simplifyS3Path(fullPath: string): string {
  return fullPath.split('/').pop() ?? fullPath;
}

/** Stable key for sort config (evidence columns share `key` but differ by type). */
export function getSortColumnKey(col: ColumnDef): string {
  if (col.key === 'evidences') return `evidences:${col.type}`;
  return col.key;
}

export function findColumnBySortKey(sortKey: string, tab: TabType): ColumnDef | undefined {
  return getSortableColumns(tab).find((col) => getSortColumnKey(col) === sortKey);
}

export function getSortableColumns(tab: TabType): ColumnDef[] {
  return RESULTS_TABLE_COLUMNS.slice(1)
    .filter((col) => !NON_SORTABLE_COLUMN_TYPES.has(col.type))
    .filter((col) => !(tab === 'pending' && col.type === 'link'))
    .filter((col) => tab !== 'submitted' || col.showInSubmitted);
}

export function isNumericSortColumn(columnKey: string, colType?: ColumnDef['type']): boolean {
  if (NUMERIC_FIELDS.includes(columnKey)) return true;
  if (columnKey === 'id' || columnKey === 'year') return true;
  return colType === 'number';
}

export function isDateSortColumn(colType?: ColumnDef['type']): boolean {
  return colType === 'date';
}

export function getSortDirectionLabels(
  columnKey: string,
  colType?: ColumnDef['type'],
): { asc: string; desc: string } {
  if (isNumericSortColumn(columnKey, colType)) {
    return { asc: 'Low → High', desc: 'High → Low' };
  }
  if (isDateSortColumn(colType)) {
    return { asc: 'Oldest → Newest', desc: 'Newest → Oldest' };
  }
  return { asc: 'A → Z', desc: 'Z → A' };
}

function isEmptySortValue(value: number | string): boolean {
  if (value === '' || value === -Infinity) return true;
  if (typeof value === 'number' && !Number.isFinite(value)) return true;
  return false;
}

/** Comparable value for a column (numeric, timestamp, or normalized text). */
export function getColumnSortValue(
  columnKey: string,
  result: BulkUploadResult,
  recordStatus?: RecordStatus,
  tab: TabType = 'pending',
  colType?: ColumnDef['type'],
): number | string {
  if (columnKey.startsWith('evidences:')) {
    const variant = columnKey.split(':')[1];
    const arr = result.evidences ?? [];
    if (variant === 'evidence_link') {
      return arr.map((e) => e.evidence_link).filter(Boolean).join(', ').toLowerCase();
    }
    return arr.map((e) => e.evidence_description).filter(Boolean).join(', ').toLowerCase();
  }

  if (columnKey === 'completeness') {
    const tokens = getColumnFilterTokens('completeness', result, recordStatus, tab);
    return (tokens[0] ?? '').toLowerCase();
  }

  const raw = getNestedValue(result, columnKey);

  if (isNumericSortColumn(columnKey, colType)) {
    const n = Number(raw);
    return Number.isFinite(n) ? n : -Infinity;
  }

  if (isDateSortColumn(colType)) {
    const s = String(raw ?? '');
    if (!s) return -Infinity;
    const t = Date.parse(s);
    return Number.isFinite(t) ? t : -Infinity;
  }

  const tokens = getColumnFilterTokens(columnKey, result, recordStatus, tab);
  if (tokens.length === 1 && tokens[0] === '(Empty)') return '';
  return tokens.join(', ').toLowerCase();
}

function compareSortValues(
  aVal: number | string,
  bVal: number | string,
  direction: SortDirection,
  isNumeric: boolean,
): number {
  const aEmpty = isEmptySortValue(aVal);
  const bEmpty = isEmptySortValue(bVal);
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;

  let cmp: number;
  if (isNumeric && typeof aVal === 'number' && typeof bVal === 'number') {
    cmp = aVal - bVal;
  } else {
    cmp = String(aVal).localeCompare(String(bVal), undefined, { sensitivity: 'base', numeric: true });
  }
  return direction === 'asc' ? cmp : -cmp;
}

export function applyTableSort(
  results: BulkUploadResult[],
  sort: TableSortConfig | null,
  recordStatuses: Record<string, RecordStatus>,
  tab: TabType,
): BulkUploadResult[] {
  if (!sort) return results;

  const col = findColumnBySortKey(sort.columnKey, tab);
  const isNumeric = isNumericSortColumn(sort.columnKey, col?.type) || isDateSortColumn(col?.type);

  return results
    .map((result, index) => ({ result, index }))
    .sort((a, b) => {
      const aVal = getColumnSortValue(
        sort.columnKey,
        a.result,
        recordStatuses[String(a.result.id)],
        tab,
        col?.type,
      );
      const bVal = getColumnSortValue(
        sort.columnKey,
        b.result,
        recordStatuses[String(b.result.id)],
        tab,
        col?.type,
      );
      const cmp = compareSortValues(aVal, bVal, sort.direction, isNumeric);
      return cmp !== 0 ? cmp : a.index - b.index;
    })
    .map(({ result }) => result);
}
