import type { UnmappedInstitution } from '../types';

/** Generates a CSV string from unmapped institutions data. */
export function createUnmappedReportCSV(unmapped: UnmappedInstitution[]): string {
  if (unmapped.length === 0) return 'No unmapped institutions found.';

  const headers: (keyof UnmappedInstitution)[] = [
    'record_id',
    'record_title',
    'source_field',
    'institution_name',
    'institution_id',
    'similarity_score',
  ];

  const rows = unmapped.map((item) =>
    headers
      .map((key) => {
        const val = item[key];
        if (val === null || val === undefined) return '';
        const str = String(val);
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return '"' + str.replace(/"/g, '""') + '"';
        }
        return str;
      })
      .join(','),
  );

  return [headers.join(','), ...rows].join('\n');
}

/** Triggers a browser CSV file download. */
export function downloadCSV(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Formats a byte count into a human-readable file size string. */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}
