'use client';

import { useEffect, useRef, useCallback } from 'react';
import type { ChangeEvent, KeyboardEvent } from 'react';
import { simplifyS3Path } from '../utils/tableHelpers';

// Hoisted static SVG (rendering-hoist-jsx)
const RefreshIconSvg = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <path d="M13.65 2.35A8 8 0 1 0 16 8h-2a6 6 0 1 1-1.76-4.24L10 6h6V0l-2.35 2.35z" />
  </svg>
);

interface S3FileSelectorProps {
  s3Objects: string[];
  selectedKey: string;
  prefix: string;
  onPrefixChange: (prefix: string) => void;
  onSelectedKeyChange: (key: string) => void;
  onRefresh: (prefix: string) => void;
}

export function S3FileSelector({
  s3Objects,
  selectedKey,
  prefix,
  onPrefixChange,
  onSelectedKeyChange,
  onRefresh,
}: S3FileSelectorProps) {
  // Debounced search (client-swr-dedup pattern - deduplicate with useRef timeout)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handlePrefixChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      onPrefixChange(value);
      if (searchTimeout.current) clearTimeout(searchTimeout.current);
      searchTimeout.current = setTimeout(() => {
        onRefresh(value);
      }, 500);
    },
    [onPrefixChange, onRefresh],
  );

  const handlePrefixKeyPress = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        if (searchTimeout.current) clearTimeout(searchTimeout.current);
        onRefresh(prefix);
      }
    },
    [onRefresh, prefix],
  );

  // Cleanup timeout on unmount (client-event-listeners cleanup)
  useEffect(() => {
    return () => {
      if (searchTimeout.current) clearTimeout(searchTimeout.current);
    };
  }, []);

  const excelObjects = s3Objects.filter(k => /\.(xlsx|xls)$/i.test(k));

  const caption =
    excelObjects.length > 0
      ? `Found ${excelObjects.length} file(s). Selected: ${simplifyS3Path(selectedKey || excelObjects[0])}`
      : 'No Excel files found.';

  return (
    <div>
      <h3 className="bulk-subsection-title">Previous file options</h3>

      <div className="bulk-form-group">
        <label htmlFor="bulkS3Prefix">Search prefix (optional)</label>
        <input
          type="text"
          id="bulkS3Prefix"
          className="bulk-form-input"
          placeholder="Enter prefix"
          value={prefix}
          onChange={handlePrefixChange}
          onKeyPress={handlePrefixKeyPress}
        />
      </div>

      <div className="bulk-form-group">
        <label htmlFor="bulkS3Select">Available files</label>
        <select
          id="bulkS3Select"
          className="bulk-form-select"
          value={selectedKey}
          onChange={(e) => onSelectedKeyChange(e.target.value)}
        >
          {excelObjects.length === 0 ? (
            <option value="">No Excel files found</option>
          ) : (
            excelObjects.map((key) => (
              <option key={key} value={key}>
                {simplifyS3Path(key)}
              </option>
            ))
          )}
        </select>
        <small className="bulk-help-text">{caption}</small>
      </div>

      <button
        className="bulk-refresh-s3-list-btn"
        type="button"
        onClick={() => onRefresh(prefix)}
      >
        {RefreshIconSvg}
        Refresh list
      </button>
    </div>
  );
}
