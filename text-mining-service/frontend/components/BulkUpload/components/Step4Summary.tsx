'use client';

import { useCallback, useEffect } from 'react';
import type { SummaryRecord } from '../types';
import { downloadSummaryExcel } from '../utils/excelUtils';
import { usePagination } from '../hooks/usePagination';

// ── Hoisted SVGs ─────────────────────────────────────────────────
const CheckCircleSvg = (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <circle cx="12" cy="12" r="10" />
    <polyline points="9 12 11 14 15 10" />
  </svg>
);

const DraftSvg = (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const ErrorSvg = (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const ExternalLinkSvg = (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden style={{ flexShrink: 0 }}>
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <polyline points="15 3 21 3 21 9" />
    <line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);

const DownloadSvg = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <path d="M8 12L3 7h3V2h4v5h3L8 12z" />
    <rect y="14" width="16" height="2" />
  </svg>
);

const FinishSvg = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

// ── Sub-components ────────────────────────────────────────────────

interface SummaryTableProps {
  records: SummaryRecord[];
  showError?: boolean;
  emptyMessage: string;
}

function SummaryTable({ records, showError, emptyMessage }: SummaryTableProps) {
  const pagination = usePagination(10);
  const { setTotalItems } = pagination;

  useEffect(() => {
    setTotalItems(records.length);
  }, [records.length, setTotalItems]);

  const { currentPage, perPage, totalPages, startIndex, endIndex } = pagination;
  const page = records.slice(startIndex, endIndex);

  const handlePerPageChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => pagination.setPerPage(parseInt(e.target.value)),
    [pagination],
  );

  if (records.length === 0) {
    return <p className="bulk-summary-empty">{emptyMessage}</p>;
  }

  return (
    <div>
      <div className="bulk-table-container">
        <table className="bulk-results-table">
          <colgroup>
            <col style={{ width: '55%' }} />
            <col style={{ width: '15%' }} />
            <col style={{ width: '15%' }} />
            <col style={{ width: '15%' }} />
          </colgroup>
          <thead>
            <tr>
              <th>Title</th>
              <th style={{ textAlign: 'center' }}>Contract Code</th>
              <th>Result Code</th>
              {showError ? <th>Error</th> : <th>STAR Link</th>}
            </tr>
          </thead>
          <tbody>
            {page.map((r) => (
              <tr key={r.id}>
                <td>{r.title}</td>
                <td style={{ textAlign: 'center' }}>{r.contract_code ?? '—'}</td>
                <td>
                  {r.result_official_code ? (
                    <span className="bulk-summary-result-code">{r.result_official_code}</span>
                  ) : (
                    <span className="bulk-summary-code-pending">Pending</span>
                  )}
                </td>
                {showError ? (
                  <td className="bulk-summary-error-cell">{r.error_message ?? '—'}</td>
                ) : (
                  <td>
                    {r.star_link ? (
                      <a
                        href={r.star_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bulk-summary-star-link"
                      >
                        Open in STAR
                        {ExternalLinkSvg}
                      </a>
                    ) : (
                      <span style={{ color: 'var(--bulk-gray-400)' }}>—</span>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {records.length > 10 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem 1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: 'var(--bulk-gray-600)', fontSize: '0.85rem' }}>
              Showing {startIndex + 1}–{endIndex} of {records.length}
            </span>
            <select
              style={{ padding: '0.35rem 0.5rem', border: '1px solid var(--bulk-gray-300)', borderRadius: 6, background: 'var(--bulk-white)', fontSize: '0.85rem' }}
              value={perPage}
              onChange={handlePerPageChange}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <button type="button" className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.85rem' }} disabled={currentPage === 1} onClick={pagination.goFirst}>&laquo;</button>
            <button type="button" className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.85rem' }} disabled={currentPage === 1} onClick={pagination.goPrev}>&lsaquo;</button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const half = Math.floor(Math.min(totalPages, 5) / 2);
              const start = Math.max(1, Math.min(currentPage - half, totalPages - Math.min(totalPages, 5) + 1));
              return start + i;
            }).map((pageNum) => (
              <button
                key={pageNum}
                type="button"
                onClick={() => pagination.goToPage(pageNum)}
                style={{
                  padding: '0.35rem 0.6rem',
                  fontSize: '0.85rem',
                  border: `1px solid ${currentPage === pageNum ? 'var(--bulk-primary)' : 'var(--bulk-gray-300)'}`,
                  background: currentPage === pageNum ? 'var(--bulk-primary)' : 'transparent',
                  color: currentPage === pageNum ? 'white' : 'var(--bulk-gray-700)',
                  borderRadius: 4,
                  cursor: 'pointer',
                  minWidth: '2rem',
                }}
              >
                {pageNum}
              </button>
            ))}
            <button type="button" className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.85rem' }} disabled={currentPage === totalPages} onClick={pagination.goNext}>&rsaquo;</button>
            <button type="button" className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.85rem' }} disabled={currentPage === totalPages} onClick={pagination.goLast}>&raquo;</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────

interface Step4SummaryProps {
  approved: SummaryRecord[];
  draft: SummaryRecord[];
  failed: SummaryRecord[];
  fileName: string;
  onBackToUnmapped: () => void;
  onFinishProcess: () => void;
}

export function Step4Summary({ approved, draft, failed, fileName, onBackToUnmapped, onFinishProcess }: Step4SummaryProps) {
  const total = approved.length + draft.length + failed.length;

  const handleDownload = () => {
    downloadSummaryExcel(approved, draft, failed, fileName);
  };

  return (
    <div className="bulk-step">
      <div className="bulk-summary-container">

        <p className="bulk-summary-intro-text">
            The following is a summary of the <strong>{total} record{total !== 1 ? 's' : ''}</strong> submitted to STAR from <strong>{fileName}</strong>.
            Approved records are immediately available in STAR. Draft records were saved but require manual review and completion before they can be submitted.
        </p>

        {/* ── Approved section ── */}
        <section className="bulk-summary-section">
          <div className="bulk-summary-section-header bulk-summary-section-header--approved">
            <div className="bulk-summary-section-title-group">
              <span className="bulk-summary-section-icon bulk-summary-section-icon--approved">{CheckCircleSvg}</span>
              <h3 className="bulk-summary-section-title">Approved Results</h3>
              <span className="bulk-summary-section-badge bulk-summary-section-badge--approved">{approved.length}</span>
            </div>
          </div>
          <SummaryTable
            records={approved}
            emptyMessage="No records were approved in this submission."
          />
        </section>

        {/* ── Draft section ── */}
        <section className="bulk-summary-section">
          <div className="bulk-summary-section-header bulk-summary-section-header--draft">
            <div className="bulk-summary-section-title-group">
              <span className="bulk-summary-section-icon bulk-summary-section-icon--draft">{DraftSvg}</span>
              <h3 className="bulk-summary-section-title">Draft Results</h3>
              <span className="bulk-summary-section-badge bulk-summary-section-badge--draft">{draft.length}</span>
            </div>
          </div>
          <SummaryTable
            records={draft}
            emptyMessage="No records were saved as draft."
          />
        </section>

        {/* ── Failed section (conditional) ── */}
        {failed.length > 0 && (
          <section className="bulk-summary-section">
            <div className="bulk-summary-section-header bulk-summary-section-header--failed">
              <div className="bulk-summary-section-title-group">
                <span className="bulk-summary-section-icon bulk-summary-section-icon--failed">{ErrorSvg}</span>
                <h3 className="bulk-summary-section-title">Failed Records</h3>
                <span className="bulk-summary-section-badge bulk-summary-section-badge--failed">{failed.length}</span>
              </div>
            </div>
            <div className="bulk-risk-notice" style={{ marginBottom: '1rem', borderColor: '#fca5a5', background: '#fff5f5' }}>
              <span style={{ fontSize: '1rem' }}>⚠️</span>
              <span>
                These records could not be submitted to STAR. Please review the error messages below and contact the STAR team if the issue persists.
              </span>
            </div>
            <SummaryTable records={failed} showError emptyMessage="" />
          </section>
        )}

        {/* ── Action row ── */}
        <div className="bulk-next-step-container bulk-summary-actions">
          <button className="bulk-download-unmapped-btn" type="button" onClick={onBackToUnmapped}>
            ← Back to Unmapped Institutions
          </button>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button className="bulk-download-unmapped-btn" type="button" onClick={handleDownload}>
              {DownloadSvg}
              Download summary (.xlsx)
            </button>
            <button className="bulk-next-step-btn" type="button" onClick={onFinishProcess}>
              {FinishSvg}
              Finish Process
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
