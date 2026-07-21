import * as XLSX from 'xlsx';
import type { SummaryRecord } from '../types';

// ── Metadata columns (full BulkUploadResult fields) ──────────────────────────
const METADATA_COLUMNS: { key: string; label: string }[] = [
  { key: 'id',                                    label: 'ID'                              },
  { key: 'title',                                 label: 'Title'                           },
  { key: 'contract_code',                         label: 'Contract Code'                   },
  { key: 'description',                           label: 'Description'                     },
  { key: 'year',                                  label: 'Year'                            },
  { key: 'training_type',                         label: 'Training Type'                   },
  { key: 'training_category',                     label: 'Training Category'               },
  { key: 'training_purpose',                      label: 'Training Purpose'                },
  { key: 'length_of_training',                    label: 'Length of Training'              },
  { key: 'degree',                                label: 'Degree'                          },
  { key: 'delivery_modality',                     label: 'Delivery Modality'               },
  { key: 'start_date',                            label: 'Start Date'                      },
  { key: 'end_date',                              label: 'End Date'                        },
  { key: 'total_participants',                    label: 'Total Participants'              },
  { key: 'male_participants',                     label: 'Male Participants'               },
  { key: 'female_participants',                   label: 'Female Participants'             },
  { key: 'non_binary_participants',               label: 'Non-binary Participants'         },
  { key: 'trainee_name',                          label: 'Trainee Name'                    },
  { key: 'trainee_gender',                        label: 'Trainee Gender'                  },
  { key: 'geoscope_level',                        label: 'Geoscope Level'                  },
  { key: 'publicity_restriction',                 label: 'Publicity Restriction'           },
  { key: 'publicity_restriction_description',     label: 'Publicity Restriction Desc.'     },
  { key: 'potential_asset',                       label: 'Potential Asset'                 },
  { key: 'potential_asset_description',           label: 'Potential Asset Desc.'           },
  { key: 'requires_further_development',          label: 'Requires Further Development'    },
  { key: 'requires_further_development_description', label: 'Further Development Desc.'   },
];

// Keys that hold arrays/objects — serialized to JSON string in the cell
const ARRAY_KEYS = new Set([
  'keywords', 'partners', 'countries', 'regions',
  'trainees_description', 'evidences',
  'main_contact_person', 'training_supervisor',
  'trainee_affiliation', 'trainee_nationality', 'language',
]);

/** Serialize a raw field value to a readable string for Excel. */
function serialize(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value);
}

function isBlankParticipantValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string' && value.trim() === '') return true;
  return false;
}

/**
 * Excel-only defaults for individual training rows (does not mutate source data).
 * Total = 1; male/female = 1 when trainee gender matches and the cell would be blank.
 */
function applyIndividualTrainingExcelDefaults(data: Record<string, unknown>): Record<string, unknown> {
  const trainingType = String(data.training_type ?? '').trim().toLowerCase();
  if (trainingType !== 'individual training') return data;

  const patched = { ...data };

  if (isBlankParticipantValue(patched.total_participants)) {
    patched.total_participants = 1;
  }

  const gender = String(patched.trainee_gender ?? '').trim().toLowerCase();
  if (gender === 'male' && isBlankParticipantValue(patched.male_participants)) {
    patched.male_participants = 1;
  }
  if (gender === 'female' && isBlankParticipantValue(patched.female_participants)) {
    patched.female_participants = 1;
  }

  return patched;
}

/** Build a row of metadata values from a SummaryRecord's rawData. */
function buildMetadataRow(r: SummaryRecord, cols: { key: string; label: string }[]): string[] {
  const raw = r.rawData as Record<string, unknown> | undefined;
  if (!raw) return cols.map(() => '');

  try {
    const data = applyIndividualTrainingExcelDefaults(raw);
    return cols.map((col) => {
      const val = data[col.key];
      if (ARRAY_KEYS.has(col.key)) return serialize(val);
      return serialize(val);
    });
  } catch {
    return cols.map((col) => {
      const val = raw[col.key];
      if (ARRAY_KEYS.has(col.key)) return serialize(val);
      return serialize(val);
    });
  }
}

function applyHeaderStyle(ws: XLSX.WorkSheet, numCols: number): void {
  for (let c = 0; c < numCols; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: 0, c });
    if (!ws[cellRef]) ws[cellRef] = { t: 's', v: '' };
    ws[cellRef].s = {
      font: { bold: true, color: { rgb: 'FFFFFF' } },
      fill: { fgColor: { rgb: '183F6F' } },
      alignment: { horizontal: 'center' },
    };
  }
}

function setColWidths(ws: XLSX.WorkSheet, numCols: number, rows: string[][]): void {
  const widths: number[] = Array(numCols).fill(10);
  for (const row of rows) {
    row.forEach((cell, i) => {
      if (cell && cell.length > widths[i]) widths[i] = cell.length;
    });
  }
  ws['!cols'] = widths.map((w) => ({ wch: Math.min(w + 14, 150) }));
}

function buildSheet(
  records: SummaryRecord[],
  extraCols: { key: string; label: string }[],
): XLSX.WorkSheet {
  // Header: metadata cols + extra (result code, star link or error)
  const allCols = [...METADATA_COLUMNS, ...extraCols];
  const header = allCols.map((c) => c.label);

  const rows = records.map((r) => {
    const meta = buildMetadataRow(r, METADATA_COLUMNS);
    const extra = extraCols.map((col) => serialize(r[col.key as keyof SummaryRecord]));
    return [...meta, ...extra];
  });

  const ws = XLSX.utils.aoa_to_sheet([header, ...rows]);
  applyHeaderStyle(ws, allCols.length);
  setColWidths(ws, allCols.length, rows);
  return ws;
}

/**
 * Downloads a summary Excel workbook with full metadata per sheet:
 * - Approved: all fields + Result Code + STAR Link
 * - Draft: all fields + Result Code + STAR Link
 * - Failed: all fields + Error message
 */
export function downloadSummaryExcel(
  approved: SummaryRecord[],
  draft: SummaryRecord[],
  failed: SummaryRecord[],
  baseFileName: string,
): void {
  const wb = XLSX.utils.book_new();

  const approvedExtras = [
    { key: 'result_official_code', label: 'Result Code' },
    { key: 'star_link',            label: 'STAR Link'   },
  ];
  const failedExtras = [
    { key: 'error_message', label: 'Error' },
  ];

  XLSX.utils.book_append_sheet(wb, buildSheet(approved, approvedExtras), 'Approved');
  XLSX.utils.book_append_sheet(wb, buildSheet(draft,    approvedExtras), 'Draft');
  if (failed.length > 0) {
    XLSX.utils.book_append_sheet(wb, buildSheet(failed, failedExtras), 'Failed');
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  const cleanBase = baseFileName.replace(/\.[^.]+$/, '');
  XLSX.writeFile(wb, `submission_summary_${cleanBase}_${timestamp}.xlsx`);
}

