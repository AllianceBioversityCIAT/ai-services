import type { UnmappedInstitution, BulkUploadResult, RecordStatus } from '../types';
import { checkCompleteness } from './completenessChecker';

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

/** Escapes a single CSV cell value. */
function escapeCell(val: unknown): string {
  if (val === null || val === undefined) return '';
  const str = typeof val === 'object' ? JSON.stringify(val) : String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

/**
 * Generates a CSV report of draft (incomplete) results to help users
 * manually complete and follow up on records that could not be auto-submitted.
 */
export function createDraftReportCSV(
  results: BulkUploadResult[],
  recordStatuses: Record<string, RecordStatus>,
): string {
  // Only results that were submitted to STAR (status complete = created in STAR)
  // AND are incomplete — these landed in STAR as Draft and need manual follow-up
  const draftResults = results.filter((r) => {
    const status = recordStatuses[String(r.id)]?.status;
    return status === 'complete' && !checkCompleteness(r).isComplete;
  });

  if (draftResults.length === 0) return 'No draft results found.';

  const headers = [
    'id',
    'star_link',
    'title',
    'description',
    'year',
    'main_contact_person',
    'keywords',
    'contract_code',
    'training_type',
    'training_category',
    'length_of_training',
    'degree',
    'total_participants',
    'male_participants',
    'female_participants',
    'non_binary_participants',
    'training_purpose',
    'trainees_description',
    'trainee_name',
    'trainee_gender',
    'trainee_affiliation',
    'trainee_nationality',
    'training_supervisor',
    'language',
    'start_date',
    'end_date',
    'delivery_modality',
    'partners',
    'geoscope_level',
    'countries',
    'regions',
    'evidences',
    'asset_ip_owner_id',
    'publicity_restriction',
    'potential_asset',
    'requires_further_development',
    'incomplete_reasons',
  ];

  const rows = draftResults.map((r) => {
    const status = recordStatuses[String(r.id)];
    const { reasons } = checkCompleteness(r);

    const getUser = (u: unknown) => {
      if (!u || typeof u !== 'object') return '';
      const user = u as { name?: string; code?: string };
      return user.name ?? '';
    };

    const getInstitution = (inst: unknown) => {
      if (!inst || typeof inst !== 'object') return '';
      const i = inst as { institution_name?: string; institution_id?: string | null };
      return i.institution_name ?? '';
    };

    const getInstitutionList = (arr: unknown) => {
      if (!Array.isArray(arr)) return '';
      return arr.map((i: unknown) => getInstitution(i)).join(' | ');
    };

    const cells: unknown[] = [
      r.id,
      status?.link ?? '',
      r.title,
      r.description,
      r.year,
      getUser(r.main_contact_person),
      Array.isArray(r.keywords) ? r.keywords.join(' | ') : '',
      r.contract_code,
      r.training_type,
      r.training_category,
      r.length_of_training,
      r.degree,
      r.total_participants,
      r.male_participants,
      r.female_participants,
      r.non_binary_participants,
      r.training_purpose,
      getInstitutionList(r.trainees_description),
      r.trainee_name,
      r.trainee_gender,
      getInstitution(r.trainee_affiliation),
      typeof r.trainee_nationality === 'object' && r.trainee_nationality !== null
        ? (r.trainee_nationality as { code?: string }).code ?? ''
        : '',
      getUser(r.training_supervisor),
      typeof r.language === 'object' && r.language !== null
        ? (r.language as { name?: string }).name ?? ''
        : '',
      r.start_date,
      r.end_date,
      r.delivery_modality,
      getInstitutionList(r.partners),
      r.geoscope_level,
      Array.isArray(r.countries)
        ? r.countries.map((c: { code: string }) => c.code).join(' | ')
        : '',
      Array.isArray(r.regions) ? r.regions.join(' | ') : '',
      Array.isArray(r.evidences)
        ? r.evidences.map((e: { evidence_link?: string }) => e.evidence_link ?? '').join(' | ')
        : '',
      r.asset_ip_owner_id,
      r.publicity_restriction,
      r.potential_asset,
      r.requires_further_development,
      reasons.join(' | '),
    ];

    return cells.map(escapeCell).join(',');
  });

  return [headers.join(','), ...rows].join('\n');
}
