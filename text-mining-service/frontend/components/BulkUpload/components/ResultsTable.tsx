'use client';

import { useCallback, useEffect, useRef, memo } from 'react';
import type { ChangeEvent } from 'react';
import type { BulkUploadResult, ColumnDef, RecordStatus, TabType } from '../types';
import { ASSET_IP_OWNER_ID_TO_NAME, RESULTS_TABLE_COLUMNS } from '../constants';
import { getNestedValue, setNestedValue, getUniqueValues } from '../utils/tableHelpers';
import { usePagination } from '../hooks/usePagination';
import { FilterPanel } from './FilterPanel';
import { useState } from 'react';
import type { RawInstitution, RawCountry } from '../types';
import { PartnersCell } from './PartnersCell';
import { SdgCell } from './SdgCell';
import { TrainingPurposeCell } from './TrainingPurposeCell';
import { RegionsCell } from './RegionsCell';
import { CountriesCell } from './CountriesCell';
import { TraineeAffiliationCell } from './TraineeAffiliationCell';
import { TraineeNationalityCell } from './TraineeNationalityCell';
import { LanguageCell } from './LanguageCell';
import { StaffCell } from './StaffCell';
import type { RawStaff } from './StaffCell';
import { EvidenceCell } from './EvidenceCell';
import type { Evidence } from './EvidenceCell';

// Hoisted static SVGs (rendering-hoist-jsx)
const StarSubmitSvg = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <path d="M8 1l2.5 5 5.5.8-4 3.9.9 5.3-4.9-2.6-4.9 2.6.9-5.3-4-3.9 5.5-.8L8 1z" />
  </svg>
);

// ---- TableCell: memoized to prevent re-renders from unrelated state (rerender-memo) ----
interface TableCellProps {
  col: ColumnDef;
  result: BulkUploadResult;
  globalIdx: number;
  recordStatus: RecordStatus | undefined;
  onEdit: (globalIdx: number, field: string, value: unknown) => void;
  authToken: string | null;
  isReadOnly?: boolean;
}

const TableCell = memo(function TableCell({ col, result, globalIdx, recordStatus, onEdit, authToken, isReadOnly }: TableCellProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea on mount
  useEffect(() => {
    if (textareaRef.current) {
      const el = textareaRef.current;
      el.style.height = 'auto';
      el.style.height = Math.max(el.scrollHeight, 60) + 'px';
    }
  }, []);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      let value: unknown = e.target.value;

      if (col.key === 'asset_ip_owner_id' && value) {
        const map: Record<string, number> = {
          'International Center for Tropical Agriculture - CIAT': 1,
          'Bioversity International': 2,
          'Bioversity International and International Center for Tropical Agriculture - CIAT': 3,
          Others: 4,
        };
        value = map[value as string] ?? value;
      }

      if (
        e.target.tagName === 'TEXTAREA' &&
        ['keywords', 'partners', 'countries', 'regions', 'sdg_targets', 'trainees_description'].includes(col.key)
      ) {
        try { value = JSON.parse(value as string); } catch { /* keep as string */ }
      }

      if ((e.target as HTMLInputElement).type === 'number') {
        value = parseInt(value as string) || 0;
      }

      if (e.target.tagName === 'TEXTAREA') {
        const el = e.target as HTMLTextAreaElement;
        el.style.height = 'auto';
        el.style.height = Math.max(el.scrollHeight, 60) + 'px';
      }

      onEdit(globalIdx, col.key, value);
    },
    [col.key, globalIdx, onEdit],
  );

  const isDisabled = !!isReadOnly || (col.enabledWhen
    ? !col.enabledWhen.values.some((v) => String(getNestedValue(result, col.enabledWhen!.field)) === String(v))
    : false);

  if (col.type === 'status') {
    const status = recordStatus?.status ?? 'pending';
    const statusClass = status === 'complete' ? 'status-complete' : status === 'failed' ? 'status-failed' : 'status-pending';
    const label = status === 'complete' ? 'Complete' : status === 'failed' ? 'Failed' : 'Pending';
    return <td><span className={statusClass}>{label}</span></td>;
  }

  if (col.type === 'link') {
    if (recordStatus?.status === 'complete' && recordStatus.link) {
      return <td><a href={recordStatus.link} target="_blank" rel="noreferrer" className="star-link">🔗 View in STAR</a></td>;
    }
    return <td>-</td>;
  }

  if (col.type === 'select') {
    let value = getNestedValue(result, col.key);
    if (col.key === 'asset_ip_owner_id' && typeof value === 'number') {
      value = ASSET_IP_OWNER_ID_TO_NAME[value as number] ?? '';
    }
    const strValue = value ? String(value) : '';
    return (
      <td>
        <select data-index={globalIdx} data-field={col.key} value={strValue} onChange={handleChange} disabled={isDisabled} className={isDisabled ? 'cell-conditional-disabled' : undefined}>
          <option value="">Select...</option>
          {(col.options ?? []).map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </td>
    );
  }

  if (col.type === 'number') {
    const value = getNestedValue(result, col.key) ?? 0;
    return (
      <td>
        <input
          type="number"
          value={Number(value)}
          min={0}
          data-index={globalIdx}
          data-field={col.key}
          onChange={handleChange}
          disabled={isDisabled}
          className={isDisabled ? 'cell-conditional-disabled' : undefined}
        />
      </td>
    );
  }

  if (col.type === 'textarea') {
    let value = getNestedValue(result, col.key);
    if (typeof value === 'object') value = JSON.stringify(value);
    return (
      <td>
        <textarea
          ref={textareaRef}
          rows={3}
          data-index={globalIdx}
          data-field={col.key}
          defaultValue={String(value ?? '')}
          onChange={handleChange}
          disabled={isDisabled}
          className={isDisabled ? 'cell-conditional-disabled' : undefined}
        />
      </td>
    );
  }

  if (col.type === 'affiliation') {
    const raw = getNestedValue(result, col.key) as RawInstitution | null | undefined;
    return (
      <td>
        <TraineeAffiliationCell value={raw} globalIdx={globalIdx} onEdit={onEdit} disabled={isDisabled} />
      </td>
    );
  }

  if (col.type === 'nationality') {
    const raw = getNestedValue(result, col.key) as { code: string } | null | undefined;
    return (
      <td>
        <TraineeNationalityCell value={raw} globalIdx={globalIdx} onEdit={onEdit} disabled={isDisabled} />
      </td>
    );
  }

  if (col.type === 'language') {
    const raw = getNestedValue(result, col.key) as { name: string; code: string } | null | undefined;
    return (
      <td>
        <LanguageCell value={raw} globalIdx={globalIdx} authToken={authToken} onEdit={onEdit} disabled={isDisabled} />
      </td>
    );
  }

  if (col.type === 'staff') {
    const raw = getNestedValue(result, col.key) as RawStaff | null | undefined;
    return (
      <td>
        <StaffCell value={raw} globalIdx={globalIdx} field={col.key} authToken={authToken} onEdit={onEdit} disabled={isDisabled} />
      </td>
    );
  }

  if (col.type === 'chips') {
    const raw = getNestedValue(result, col.key);
    const items: string[] = Array.isArray(raw)
      ? raw.map(String)
      : typeof raw === 'string' && raw.trim().startsWith('[')
        ? (() => { try { return JSON.parse(raw) as string[]; } catch { return [raw]; } })()
        : raw ? [String(raw)] : [];
    return (
      <td>
        <div className="bulk-chips">
          {items.map((item, i) => (
            <span key={i} className="bulk-chip">{item}</span>
          ))}
          {items.length === 0 && <span className="bulk-chips-empty">—</span>}
        </div>
      </td>
    );
  }

  if (col.type === 'partners') {
    const raw = getNestedValue(result, col.key);
    const partners: RawInstitution[] = Array.isArray(raw) ? (raw as RawInstitution[]) : [];
    return (
      <td className={isReadOnly ? 'bulk-cell-readonly' : undefined}>
        <PartnersCell
          partners={partners}
          globalIdx={globalIdx}
          field={col.key}
          onEdit={onEdit as (globalIdx: number, field: string, value: RawInstitution[]) => void}
        />
      </td>
    );
  }

  if (col.type === 'training_purpose') {
    const raw = getNestedValue(result, col.key);
    return (
      <td>
        <TrainingPurposeCell
          value={raw !== undefined && raw !== null ? String(raw) : undefined}
          globalIdx={globalIdx}
          onEdit={onEdit as (globalIdx: number, field: string, value: string) => void}
          disabled={isDisabled}
        />
      </td>
    );
  }

  if (col.type === 'regions') {
    const raw = getNestedValue(result, col.key);
    const regionCodes: number[] = Array.isArray(raw)
      ? (raw as unknown[]).map(r => typeof r === 'object' && r !== null && 'id' in r ? Number((r as {id:unknown}).id) : Number(r)).filter(n => !isNaN(n))
      : typeof raw === 'string' && raw.trim().startsWith('[')
        ? (() => { try { return (JSON.parse(raw) as unknown[]).map(Number).filter(n => !isNaN(n)); } catch { return []; } })()
        : [];
    const geoscopeLevel = String(getNestedValue(result, 'geoscope_level') ?? '');
    const isRegional = geoscopeLevel === 'Regional' || geoscopeLevel === 'Global';
    if (!isRegional) {
      return <td><span className="geo-readonly">{regionCodes.length ? regionCodes.join(', ') : '—'}</span></td>;
    }
    return (
      <td className={isReadOnly ? 'bulk-cell-readonly' : undefined}>
        <RegionsCell
          values={regionCodes}
          globalIdx={globalIdx}
          onEdit={onEdit as (globalIdx: number, field: string, value: number[]) => void}
        />
      </td>
    );
  }

  if (col.type === 'countries') {
    const raw = getNestedValue(result, col.key);
    const countriesVal: RawCountry[] = Array.isArray(raw)
      ? (raw as RawCountry[])
      : typeof raw === 'string' && raw.trim().startsWith('[')
        ? (() => { try { return JSON.parse(raw) as RawCountry[]; } catch { return []; } })()
        : [];
    const geoscopeLevel = String(getNestedValue(result, 'geoscope_level') ?? '');
    const isGeoEditable = geoscopeLevel === 'National' || geoscopeLevel === 'Sub-national' || geoscopeLevel === 'Global';
    if (!isGeoEditable) {
      return <td><span className="geo-readonly">{countriesVal.length ? countriesVal.map(c => c.code).join(', ') : '—'}</span></td>;
    }
    return (
      <td className={isReadOnly ? 'bulk-cell-readonly' : undefined}>
        <CountriesCell
          values={countriesVal}
          geoscopeLevel={geoscopeLevel}
          globalIdx={globalIdx}
          authToken={authToken}
          onEdit={onEdit as (globalIdx: number, field: string, value: RawCountry[]) => void}
        />
      </td>
    );
  }

  if (col.type === 'evidence_desc' || col.type === 'evidence_link') {
    const raw = getNestedValue(result, col.key);
    const evidences: Evidence[] = Array.isArray(raw)
      ? (raw as Evidence[])
      : typeof raw === 'string' && raw.trim().startsWith('[')
        ? (() => { try { return JSON.parse(raw) as Evidence[]; } catch { return []; } })()
        : [];
    const field = col.type === 'evidence_desc' ? 'evidence_description' : 'evidence_link';
    return (
      <td className={isReadOnly ? 'bulk-cell-readonly' : undefined}>
        <EvidenceCell
          evidences={evidences}
          field={field}
          globalIdx={globalIdx}
          onEdit={onEdit as (globalIdx: number, field: string, value: Evidence[]) => void}
        />
      </td>
    );
  }

  if (col.type === 'sdg') {
    const raw = getNestedValue(result, col.key);
    const values: string[] = Array.isArray(raw)
      ? (raw as string[])
      : typeof raw === 'string' && raw.trim().startsWith('[')
        ? (() => { try { return JSON.parse(raw) as string[]; } catch { return raw ? [raw] : []; } })()
        : raw ? [String(raw)] : [];
    return (
      <td className={isReadOnly ? 'bulk-cell-readonly' : undefined}>
        <SdgCell
          values={values}
          globalIdx={globalIdx}
          onEdit={onEdit as (globalIdx: number, field: string, value: string[]) => void}
        />
      </td>
    );
  }

  if (col.type === 'date') {
    const raw = getNestedValue(result, col.key);
    const dateVal = raw ? String(raw) : '';
    return (
      <td>
        <input
          type="date"
          defaultValue={dateVal}
          data-index={globalIdx}
          data-field={col.key}
          onChange={handleChange}
          disabled={isDisabled}
        />
      </td>
    );
  }

  // text / readonly
  const value = getNestedValue(result, col.key) ?? '';
  if (col.readonly) {
    return (
      <td>
        <input type="text" value={String(value)} readOnly style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }} />
      </td>
    );
  }
  return (
    <td>
      <input
        type="text"
        defaultValue={String(value)}
        data-index={globalIdx}
        data-field={col.key}
        onChange={handleChange}
        disabled={isDisabled}
        className={isDisabled ? 'cell-conditional-disabled' : undefined}
      />
    </td>
  );
});

// ---- ResultsTable ----
interface ResultsTableProps {
  results: BulkUploadResult[];
  editedData: BulkUploadResult[];
  recordStatuses: Record<string, RecordStatus>;
  activeFilters: Record<string, string[]>;
  currentTab: TabType;
  filteredResults: BulkUploadResult[];
  selectedIndices: Set<number>;
  onEdit: (globalIdx: number, field: string, value: unknown) => void;
  onSelectionChange: React.Dispatch<React.SetStateAction<Set<number>>>;
  onFilterApply: (columnKey: string, values: string[]) => void;
  onFilterClear: (columnKey: string) => void;
  onTabChange: (tab: TabType) => void;
  onSubmitToStar: () => void;
  onClearSelections: () => void;
  onViewUnmapped: () => void;
  starSubmissionResponse: unknown;
  authToken: string | null;
}

export function ResultsTable({
  results,
  editedData,
  recordStatuses,
  activeFilters,
  currentTab,
  filteredResults,
  selectedIndices,
  onEdit,
  onSelectionChange,
  onFilterApply,
  onFilterClear,
  onTabChange,
  onSubmitToStar,
  onClearSelections,
  onViewUnmapped,
  starSubmissionResponse,
  authToken,
}: ResultsTableProps) {
  const pagination = usePagination(10);
  const { setTotalItems } = pagination;

  // Sync totalItems via effect to avoid setState-during-render
  useEffect(() => {
    setTotalItems(filteredResults.length);
  }, [filteredResults.length, setTotalItems]);

  const { currentPage, perPage, totalPages, startIndex, endIndex } = pagination;

  const [openFilter, setOpenFilter] = useState<{ key: string; rect: DOMRect } | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const handleSubmitClick = useCallback(() => setShowConfirmModal(true), []);

  const handleConfirmSubmit = useCallback(() => {
    setShowConfirmModal(false);
    onSubmitToStar();
  }, [onSubmitToStar]);

  const handleCancelSubmit = useCallback(() => setShowConfirmModal(false), []);

  const paginatedResults = filteredResults.slice(startIndex, endIndex);

  // Map filtererd result to its original editedData index for correct editing
  const globalIndexMap = useCallback(
    (localIdx: number): number => {
      const item = filteredResults[startIndex + localIdx];
      return editedData.findIndex((r) => r === item || r.id === item?.id);
    },
    [filteredResults, editedData, startIndex],
  );

  const handleSelectAll = useCallback(
    (checked: boolean) => {
      // rerender-functional-setstate
      onSelectionChange((prev: Set<number>) => {
        const next = new Set(prev);
        paginatedResults.forEach((_, localIdx) => {
          const globalIdx = globalIndexMap(localIdx);
          if (checked) next.add(globalIdx);
          else next.delete(globalIdx);
        });
        return next;
      });
    },
    [paginatedResults, globalIndexMap, onSelectionChange],
  ) as unknown as (checked: boolean) => void;

  const handleRowCheck = useCallback(
    (globalIdx: number, checked: boolean) => {
      onSelectionChange((prev: Set<number>) => {
        const next = new Set(prev);
        if (checked) next.add(globalIdx);
        else next.delete(globalIdx);
        return next;
      });
    },
    [onSelectionChange],
  ) as unknown as (idx: number, checked: boolean) => void;

  const openFilterPanel = useCallback((columnKey: string, e: React.MouseEvent<HTMLSpanElement>) => {
    const rect = (e.currentTarget as HTMLSpanElement).getBoundingClientRect();
    setOpenFilter((prev) => (prev?.key === columnKey ? null : { key: columnKey, rect }));
  }, []);

  const closeFilter = useCallback(() => setOpenFilter(null), []);

  const pageAllSelected = paginatedResults.every((_, i) => selectedIndices.has(globalIndexMap(i)));

  return (
    <div className="bulk-step">
      {/* Tabs */}
      <div className="bulk-results-tabs">
        <button
          className={`bulk-tab-btn${currentTab === 'pending' ? ' active' : ''}`}
          type="button"
          onClick={() => { pagination.reset(); onTabChange('pending'); }}
        >
          Pending Results
        </button>
        <button
          className={`bulk-tab-btn${currentTab === 'submitted' ? ' active' : ''}`}
          type="button"
          onClick={() => { pagination.reset(); onTabChange('submitted'); }}
        >
          Submitted Results
        </button>
      </div>

      {/* Controls row — only shown on pending tab */}
      {currentTab === 'pending' && (
        <div className="bulk-results-controls">
          <button
            className="bulk-unmapped-nav-btn"
            type="button"
            disabled={selectedIndices.size === 0}
            onClick={onClearSelections}
          >
            🔄 Clear Selections
          </button>
          <button
            className="bulk-star-submit-btn"
            type="button"
            disabled={selectedIndices.size === 0}
            onClick={handleSubmitClick}
          >
            {StarSubmitSvg}
            Submit to STAR
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bulk-table-container">
        <table id="bulkResultsTable" className="bulk-results-table">
          <colgroup>
            {currentTab === 'pending' && <col style={{ width: RESULTS_TABLE_COLUMNS[0].width }} />}
            {RESULTS_TABLE_COLUMNS.slice(1).map((col) => (
              <col key={col.key + col.type} style={{ width: col.width }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {currentTab === 'pending' && (
                <th>
                  <input
                    type="checkbox"
                    title="Select/Deselect All"
                    checked={pageAllSelected && paginatedResults.length > 0}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                  />
                </th>
              )}
              {RESULTS_TABLE_COLUMNS.slice(1).map((col) => {
                if (col.readonly || col.type === 'status' || col.type === 'link') {
                  return <th key={col.key + col.type}>{col.label}</th>;
                }
                const hasFilter = activeFilters[col.key]?.length > 0;
                return (
                  <th key={col.key + col.type}>
                    <div className="th-content">
                      <span>
                        {col.tooltip
                          ? <>{col.label.replace(' ⓘ', '')} <span className="col-tooltip-icon" data-tooltip={col.tooltip}>ⓘ</span></>
                          : col.label}
                      </span>
                      <span
                        className={`filter-icon${hasFilter ? ' filter-active' : ''}`}
                        title="Filter"
                        onClick={(e) => openFilterPanel(col.key, e)}
                        style={{ cursor: 'pointer' }}
                      >
                        ▼
                      </span>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {paginatedResults.map((result, localIdx) => {
              const globalIdx = globalIndexMap(localIdx);
              const rid = String(result.id);
              return (
                <tr key={rid || localIdx}>
                  {currentTab === 'pending' && (
                    <td>
                      <input
                        type="checkbox"
                        className="row-select"
                        checked={selectedIndices.has(globalIdx)}
                        onChange={(e) => handleRowCheck(globalIdx, e.target.checked)}
                      />
                    </td>
                  )}
                  {RESULTS_TABLE_COLUMNS.slice(1).map((col) => (
                    <TableCell
                      key={col.key + col.type}
                      col={col}
                      result={result}
                      globalIdx={globalIdx}
                      recordStatus={recordStatuses[rid]}
                      onEdit={onEdit}
                      authToken={authToken}
                      isReadOnly={currentTab === 'submitted'}
                    />
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ color: 'var(--bulk-gray-600)', fontSize: '0.9rem' }}>
            Showing {startIndex + 1}–{endIndex} of {filteredResults.length} records
          </span>
          <select
            style={{ padding: '0.5rem', border: '1px solid var(--bulk-gray-300)', borderRadius: 6, background: 'var(--bulk-white)' }}
            value={perPage}
            onChange={(e) => pagination.setPerPage(parseInt(e.target.value))}
          >
            {[10, 25, 50, 100, 200].map((n) => (
              <option key={n} value={n}>{n} per page</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button type="button" className="btn btn-secondary" style={{ padding: '0.5rem 0.75rem' }} disabled={currentPage === 1} onClick={pagination.goFirst}>⟪ First</button>
          <button type="button" className="btn btn-secondary" style={{ padding: '0.5rem 0.75rem' }} disabled={currentPage === 1} onClick={pagination.goPrev}>← Previous</button>
          <span style={{ color: 'var(--bulk-gray-700)', fontWeight: 500, padding: '0 1rem' }}>Page {currentPage} of {totalPages}</span>
          <button type="button" className="btn btn-secondary" style={{ padding: '0.5rem 0.75rem' }} disabled={currentPage === totalPages} onClick={pagination.goNext}>Next →</button>
          <button type="button" className="btn btn-secondary" style={{ padding: '0.5rem 0.75rem' }} disabled={currentPage === totalPages} onClick={pagination.goLast}>Last ⟫</button>
        </div>
      </div>

      {selectedIndices.size > 0 && (
        <div className="bulk-selection-info">
          📋 Selected: {selectedIndices.size} of {filteredResults.length} records
        </div>
      )}

      {/* STAR Submission Results — logged to console only */}
      {starSubmissionResponse !== null && currentTab === 'pending' && (() => {
        console.log('STAR Submission Results:', starSubmissionResponse);
        return null;
      })()}

      {/* Next step — navigates to unmapped institutions */}
      {currentTab === 'pending' && (
        <div className="bulk-next-step-container">
          <button className="bulk-next-step-btn" type="button" onClick={onViewUnmapped}>
            Next step
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
              <path d="M8 1l7 7-7 7" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      )}

      {/* STAR Submission Confirmation Modal */}
      {showConfirmModal && (
        <div className="bulk-confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="bulk-confirm-title">
          <div className="bulk-confirm-modal">
            <h3 id="bulk-confirm-title" className="bulk-confirm-title">Submit to STAR?</h3>
            <p className="bulk-confirm-desc">
              You are about to send{' '}
              <strong>{selectedIndices.size} record{selectedIndices.size !== 1 ? 's' : ''}</strong>{' '}
              directly to <strong>STAR</strong>. This action cannot be undone.
            </p>
            <p className="bulk-confirm-sub">Please confirm that the selected entries are ready for submission.</p>
            <div className="bulk-confirm-actions">
              <button className="bulk-confirm-btn-cancel" type="button" onClick={handleCancelSubmit}>
                Cancel
              </button>
              <button className="bulk-confirm-btn-submit" type="button" onClick={handleConfirmSubmit}>
                {StarSubmitSvg}
                Yes, submit to STAR
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter Panel Portal */}
      {openFilter !== null && (
        <FilterPanel
          columnKey={openFilter.key}
          uniqueValues={getUniqueValues(results, openFilter.key)}
          currentFilters={activeFilters[openFilter.key] ?? []}
          anchorRect={openFilter.rect}
          onApply={onFilterApply}
          onClear={onFilterClear}
          onClose={closeFilter}
        />
      )}
    </div>
  );
}
