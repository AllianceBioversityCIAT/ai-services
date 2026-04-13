'use client';

import { useCallback, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent } from 'react';
import { formatFileSize } from '../utils/csvUtils';

function isValidExcelFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith('.xlsx') || name.endsWith('.xls');
}

// Hoisted static SVGs (rendering-hoist-jsx)
const DropzonePlus = (
  <svg width="60" height="60" viewBox="0 0 48 48" fill="none" aria-hidden>
    <circle cx="24" cy="24" r="23" stroke="#00B6FF" strokeWidth="2" />
    <path d="M24 16v16M16 24h16" stroke="#00B6FF" strokeWidth="2" />
  </svg>
);

const FileIconLarge = (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="#00B6FF" aria-hidden>
    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
  </svg>
);

const RemoveIconSvg = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
  </svg>
);

interface FileDropzoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File) => void;
  onFileRemove: () => void;
}

export function FileDropzone({ selectedFile, onFileSelect, onFileRemove }: FileDropzoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showInvalidModal, setShowInvalidModal] = useState(false);

  const rejectFile = useCallback((inputEl: HTMLInputElement | null) => {
    if (inputEl) inputEl.value = '';
    setShowInvalidModal(true);
  }, []);

  const handleFileChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      if (!isValidExcelFile(file)) {
        rejectFile(e.target);
        return;
      }
      onFileSelect(file);
    },
    [onFileSelect, rejectFile],
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--bulk-primary-light)';
    (e.currentTarget as HTMLDivElement).style.background = 'var(--bulk-white)';
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    (e.currentTarget as HTMLDivElement).style.borderColor = '#BFDBFE';
    (e.currentTarget as HTMLDivElement).style.background = 'var(--bulk-bg-light)';
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      (e.currentTarget as HTMLDivElement).style.borderColor = '#BFDBFE';
      (e.currentTarget as HTMLDivElement).style.background = 'var(--bulk-bg-light)';
      const file = e.dataTransfer.files?.[0];
      if (!file) return;
      if (!isValidExcelFile(file)) {
        rejectFile(fileInputRef.current);
        return;
      }
      // Sync the native input so form state is consistent
      if (fileInputRef.current) {
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInputRef.current.files = dt.files;
      }
      onFileSelect(file);
    },
    [onFileSelect, rejectFile],
  );

  const handleRemove = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (fileInputRef.current) fileInputRef.current.value = '';
      onFileRemove();
    },
    [onFileRemove],
  );

  return (
    <div>
      {showInvalidModal && (
        <div className="bulk-invalid-file-overlay" role="dialog" aria-modal="true" aria-labelledby="bulk-invalid-file-title">
          <div className="bulk-invalid-file-modal">
            <div className="bulk-invalid-file-icon">❌</div>
            <h3 id="bulk-invalid-file-title" className="bulk-invalid-file-title">Invalid file type</h3>
            <p className="bulk-invalid-file-desc">
              Only <strong>.xlsx</strong> and <strong>.xls</strong> files are accepted.<br />
              Please select a valid Excel file.
            </p>
            <button
              className="bulk-invalid-file-btn"
              type="button"
              onClick={() => setShowInvalidModal(false)}
            >
              Got it
            </button>
          </div>
        </div>
      )}

      <div
        className="bulk-upload-dropzone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          id="bulkFileInput"
          accept=".xlsx,.xls"
          hidden
          onChange={handleFileChange}
        />

        {selectedFile !== null ? (
          /* File selected — show preview card inside the dropzone */
          <div className="bulk-file-preview-card">
            <div className="bulk-file-preview-icon">{FileIconLarge}</div>
            <div className="bulk-file-preview-name">{selectedFile.name}</div>
            <div className="bulk-file-preview-size">{formatFileSize(selectedFile.size)}</div>
            <button className="bulk-file-remove-btn" type="button" onClick={handleRemove} aria-label="Remove file">
              {RemoveIconSvg}
            </button>
          </div>
        ) : (
          /* No file — show drag/drop prompt */
          <label htmlFor="bulkFileInput" className="bulk-dropzone-label">
            <div className="bulk-dropzone-icon">{DropzonePlus}</div>
            <p className="bulk-dropzone-text">Drag and drop your file here or click to upload</p>
            <p className="bulk-dropzone-subtext">Accepted file formats: xlsx, xls</p>
          </label>
        )}
      </div>
    </div>
  );
}
