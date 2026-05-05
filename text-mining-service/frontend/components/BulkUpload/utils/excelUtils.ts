import * as XLSX from 'xlsx';
import type { SummaryRecord } from '../types';

const APPROVED_COLUMNS = [
  { key: 'title',                label: 'Title'          },
  { key: 'contract_code',        label: 'Contract Code'  },
  { key: 'result_official_code', label: 'Result Code'    },
  { key: 'star_link',            label: 'STAR Link'      },
];

const DRAFT_COLUMNS = [
  { key: 'title',                label: 'Title'          },
  { key: 'contract_code',        label: 'Contract Code'  },
  { key: 'result_official_code', label: 'Result Code'    },
  { key: 'star_link',            label: 'STAR Link'      },
];

const FAILED_COLUMNS = [
  { key: 'title',         label: 'Title'         },
  { key: 'contract_code', label: 'Contract Code' },
  { key: 'error_message', label: 'Error'         },
];

function buildSheetData(
  records: SummaryRecord[],
  columns: { key: string; label: string }[],
): (string | undefined)[][] {
  const header = columns.map((c) => c.label);
  const rows = records.map((r) =>
    columns.map((c) => r[c.key as keyof SummaryRecord] as string | undefined),
  );
  return [header, ...rows];
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

function setColWidths(
  ws: XLSX.WorkSheet,
  columns: { key: string; label: string }[],
  records: SummaryRecord[],
): void {
  ws['!cols'] = columns.map((col) => {
    const maxLen = Math.max(
      col.label.length,
      ...records.map((r) => String(r[col.key as keyof SummaryRecord] ?? '').length),
    );
    return { wch: Math.min(maxLen + 4, 60) };
  });
}

/**
 * Downloads a summary Excel workbook with three sheets:
 * - Approved: records submitted and approved
 * - Draft: records submitted but saved as draft
 * - Failed: records that could not be submitted
 */
export function downloadSummaryExcel(
  approved: SummaryRecord[],
  draft: SummaryRecord[],
  failed: SummaryRecord[],
  baseFileName: string,
): void {
  const wb = XLSX.utils.book_new();

  // ── Approved sheet ──────────────────────────────────
  const approvedData = buildSheetData(approved, APPROVED_COLUMNS);
  const wsApproved = XLSX.utils.aoa_to_sheet(approvedData);
  applyHeaderStyle(wsApproved, APPROVED_COLUMNS.length);
  setColWidths(wsApproved, APPROVED_COLUMNS, approved);
  XLSX.utils.book_append_sheet(wb, wsApproved, 'Approved');

  // ── Draft sheet ─────────────────────────────────────
  const draftData = buildSheetData(draft, DRAFT_COLUMNS);
  const wsDraft = XLSX.utils.aoa_to_sheet(draftData);
  applyHeaderStyle(wsDraft, DRAFT_COLUMNS.length);
  setColWidths(wsDraft, DRAFT_COLUMNS, draft);
  XLSX.utils.book_append_sheet(wb, wsDraft, 'Draft');

  // ── Failed sheet (only if there are failures) ───────
  if (failed.length > 0) {
    const failedData = buildSheetData(failed, FAILED_COLUMNS);
    const wsFailed = XLSX.utils.aoa_to_sheet(failedData);
    applyHeaderStyle(wsFailed, FAILED_COLUMNS.length);
    setColWidths(wsFailed, FAILED_COLUMNS, failed);
    XLSX.utils.book_append_sheet(wb, wsFailed, 'Failed');
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  const cleanBase = baseFileName.replace(/\.[^.]+$/, '');
  XLSX.writeFile(wb, `submission_summary_${cleanBase}_${timestamp}.xlsx`);
}
