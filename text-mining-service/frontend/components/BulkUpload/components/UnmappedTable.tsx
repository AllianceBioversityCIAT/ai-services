'use client';

import { useCallback, useEffect } from 'react';
import type { UnmappedInstitution } from '../types';
import { usePagination } from '../hooks/usePagination';

// Hoisted SVG (rendering-hoist-jsx)
const DownloadSvg = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <path d="M8 12L3 7h3V2h4v5h3L8 12z" />
    <rect y="14" width="16" height="2" />
  </svg>
);

const NextArrowSvg = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <path d="M6 12l4-4-4-4v8z" />
  </svg>
);

interface UnmappedTableProps {
  institutions: UnmappedInstitution[];
  onDownloadReport: () => void;
  onNextStep: () => void;
}

export function UnmappedTable({ institutions, onDownloadReport, onNextStep }: UnmappedTableProps) {
  const pagination = usePagination(5);
  const { setTotalItems } = pagination;

  // Sync totalItems via effect to avoid setState-during-render
  useEffect(() => {
    setTotalItems(institutions.length);
  }, [institutions.length, setTotalItems]);

  const { currentPage, perPage, totalPages, startIndex, endIndex } = pagination;
  const page = institutions.slice(startIndex, endIndex);

  const handlePerPageChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      pagination.setPerPage(parseInt(e.target.value));
    },
    [pagination],
  );

  const handlePageBtn = useCallback(
    (pageNum: number) => pagination.goToPage(pageNum),
    [pagination],
  );

  return (
    <div className="bulk-step">
      <div className="bulk-unmapped-container">
        <div className="bulk-unmapped-header">
          <span className="bulk-unmapped-info">
            Showing {startIndex + 1}–{endIndex} of {institutions.length} unmapped institutions
          </span>
          <button className="bulk-download-unmapped-btn" type="button" onClick={onDownloadReport}>
            {DownloadSvg}
            Download unmapped institutions report
          </button>
        </div>

        <div className="bulk-table-container">
          <table className="bulk-results-table">
            <thead>
              <tr>
                <th>Record ID</th>
                <th>Record title</th>
                <th>Source field</th>
                <th>Institution name</th>
                <th>Institution ID</th>
                <th>Similarity score</th>
              </tr>
            </thead>
            <tbody>
              {page.map((item, i) => (
                <tr key={`${item.record_id}-${item.institution_name}-${i}`}>
                  <td style={{ padding: '1rem' }}>{item.record_id}</td>
                  <td style={{ padding: '1rem' }}>{item.record_title}</td>
                  <td style={{ padding: '1rem' }}>{item.source_field}</td>
                  <td style={{ padding: '1rem' }}>{item.institution_name}</td>
                  <td style={{ padding: '1rem' }}>{item.institution_id ?? 'null'}</td>
                  <td style={{ padding: '1rem' }}>{item.similarity_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: 'var(--bulk-gray-600)', fontSize: '0.9rem' }}>
              Showing {startIndex + 1}–{endIndex} of {institutions.length} results
            </span>
            <select
              style={{ padding: '0.5rem', border: '1px solid var(--bulk-gray-300)', borderRadius: 6, background: 'var(--bulk-white)' }}
              value={perPage}
              onChange={handlePerPageChange}
            >
              <option value={5}>05</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {Array.from({ length: Math.min(totalPages, 4) }, (_, i) => i + 1).map((pageNum) => (
              <button
                key={pageNum}
                type="button"
                onClick={() => handlePageBtn(pageNum)}
                style={{
                  padding: '0.5rem 0.75rem',
                  border: `1px solid ${currentPage === pageNum ? 'var(--bulk-primary)' : 'var(--bulk-gray-300)'}`,
                  background: currentPage === pageNum ? 'var(--bulk-primary)' : 'transparent',
                  color: currentPage === pageNum ? 'white' : 'var(--bulk-gray-700)',
                  borderRadius: 4,
                  cursor: 'pointer',
                }}
              >
                {pageNum}
              </button>
            ))}
            {totalPages > 4 && <span style={{ padding: '0 0.5rem' }}>...</span>}
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.5rem 0.75rem' }}
              disabled={currentPage === totalPages}
              onClick={pagination.goNext}
            >
              &gt;
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.5rem 0.75rem' }}
              disabled={currentPage === totalPages}
              onClick={pagination.goLast}
            >
              &gt;&gt;
            </button>
          </div>
        </div>

        {/* Next Step */}
        <div className="bulk-next-step-container">
          <button className="bulk-next-step-btn" type="button" onClick={onNextStep}>
            Next step
            {NextArrowSvg}
          </button>
        </div>
      </div>
    </div>
  );
}
