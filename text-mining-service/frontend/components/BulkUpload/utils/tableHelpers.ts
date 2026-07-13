import type { BulkUploadResult, ColumnDef, RawInstitution, RawUser, RawLanguage, RawCountry, RawEvidence, RecordStatus, TabType } from '../types';
import { checkCompleteness } from './completenessChecker';

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
