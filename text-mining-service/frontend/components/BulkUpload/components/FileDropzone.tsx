'use client';

import { useCallback, useRef } from 'react';
import type { ChangeEvent, DragEvent } from 'react';
import { formatFileSize } from '../utils/csvUtils';

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

  const handleFileChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect],
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--bulk-primary-light)';
    (e.currentTarget as HTMLDivElement).style.background = 'var(--bulk-white)';
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--bulk-gray-300)';
    (e.currentTarget as HTMLDivElement).style.background = 'var(--bulk-gray-50)';
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--bulk-gray-300)';
      (e.currentTarget as HTMLDivElement).style.background = 'var(--bulk-gray-50)';
      const file = e.dataTransfer.files?.[0];
      if (file) {
        // Sync the native input so form state is consistent
        if (fileInputRef.current) {
          const dt = new DataTransfer();
          dt.items.add(file);
          fileInputRef.current.files = dt.files;
        }
        onFileSelect(file);
      }
    },
    [onFileSelect],
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
        <label htmlFor="bulkFileInput" className="bulk-dropzone-label">
          <div className="bulk-dropzone-icon">{DropzonePlus}</div>
          <p className="bulk-dropzone-text">Drag and drop your file here or click to upload</p>
          <p className="bulk-dropzone-subtext">Accepted file formats: xlsx, xls</p>
        </label>
      </div>

      {selectedFile !== null && (
        <div className="bulk-file-preview-card">
          <div className="bulk-file-preview-icon">{FileIconLarge}</div>
          <div className="bulk-file-preview-info">
            <div className="bulk-file-preview-name">{selectedFile.name}</div>
            <div className="bulk-file-preview-size">{formatFileSize(selectedFile.size)}</div>
          </div>
          <button className="bulk-file-remove-btn" type="button" onClick={handleRemove} aria-label="Remove file">
            {RemoveIconSvg}
          </button>
        </div>
      )}
    </div>
  );
}
