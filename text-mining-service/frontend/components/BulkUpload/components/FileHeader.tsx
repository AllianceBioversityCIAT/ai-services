'use client';

// Hoisted static SVG (rendering-hoist-jsx)
const FileIconSvg = (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="#00B6FF" aria-hidden>
    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
  </svg>
);

const InfoIconSvg = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
    <path d="M8.5 5h-1v4h1V5z" />
    <path d="M8 11.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1z" />
  </svg>
);

interface FileHeaderProps {
  fileName: string;
  onNewUpload: () => void;
}

export function FileHeader({ fileName, onNewUpload }: FileHeaderProps) {
  return (
    <div className="bulk-results-file-header">
      <div className="bulk-file-info">
        {FileIconSvg}
        <span className="bulk-processed-file-name">{fileName}</span>
      </div>
      <button className="bulk-new-upload-btn" onClick={onNewUpload} type="button">
        {InfoIconSvg}
        New upload
      </button>
    </div>
  );
}
