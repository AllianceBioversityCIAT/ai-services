import type { BulkUploadResult } from '../types';

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

/** Serializes a cell value to a stable display string for filter comparison. */
export function formatCellValueForFilter(value: unknown): string {
  if (value === null || value === undefined) return '(Empty)';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/** Returns sorted unique display-string values for a column across all rows. */
export function getUniqueValues(results: BulkUploadResult[], columnKey: string): string[] {
  const values = new Set<string>();
  for (const result of results) {
    values.add(formatCellValueForFilter(getNestedValue(result, columnKey)));
  }
  return Array.from(values).sort();
}

/** Simplifies an S3 full path to a readable label. */
export function simplifyS3Path(fullPath: string): string {
  if (fullPath.includes('bulk_upload/')) {
    return fullPath.substring(fullPath.indexOf('bulk_upload/'));
  }
  if (fullPath.includes('test/')) {
    return fullPath.substring(fullPath.indexOf('test/'));
  }
  return fullPath.split('/').pop() ?? fullPath;
}
