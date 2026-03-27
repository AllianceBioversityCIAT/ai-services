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

  const caption =
    s3Objects.length > 0
      ? `Found ${s3Objects.length} file(s). Selected: ${simplifyS3Path(selectedKey || s3Objects[0])}`
      : 'No files found.';

  return (
    <div>
      <h3 className="bulk-subsection-title">Select file</h3>

      <div className="bulk-form-group">
        <label htmlFor="bulkS3Prefix">Search prefix (optional)</label>
        <input
          type="text"
          id="bulkS3Prefix"
          className="bulk-form-input"
          placeholder="Enter folder path or prefix"
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
          {s3Objects.length === 0 ? (
            <option value="">No files found</option>
          ) : (
            s3Objects.map((key) => (
              <option key={key} value={key}>
                {simplifyS3Path(key)}
              </option>
            ))
          )}
        </select>
        <small className="bulk-help-text">{caption}</small>
      </div>

      <button
        className="bulk-btn bulk-btn-secondary"
        type="button"
        onClick={() => onRefresh(prefix)}
      >
        {RefreshIconSvg}
        Refresh list
      </button>

      <div className="bulk-info-text" style={{ marginTop: '1rem' }}>
        ℹ️ Files are loaded from S3 bucket. Make sure your file is uploaded before processing.
      </div>
    </div>
  );
}
