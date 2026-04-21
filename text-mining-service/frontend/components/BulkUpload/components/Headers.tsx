'use client';

import { FileHeader } from './FileHeader';

// Hoisted static JSX (rendering-hoist-jsx)
const PageHeader = (
  <>
    <div className="bulk-content-header">
      <h1 className="bulk-page-title">Upload multiple Capacity Development entries within a specific bilateral</h1>
    </div>
    <div className="bulk-info-banner">
      <div className="bulk-info-icon">i</div>
      <div className="bulk-info-text">
        This module is currently part of a pilot phase, where the process is being tested with a limited and controlled group of users, specifically Admins and MEL Focal Points, in close collaboration with the STAR technical team. It uses AI-powered processing to extract and map information, so all results should be carefully reviewed before submission to ensure accuracy.
      </div>
    </div>
  </>
);

export function UploadHeader() {
  return <div>{PageHeader}</div>;
}

interface UnmappedHeaderProps {
  fileName: string;
  unmappedCount: number;
  onNewUpload: () => void;
}

export function UnmappedHeader({ fileName, unmappedCount, onNewUpload }: UnmappedHeaderProps) {
  return (
    <div>
      <FileHeader fileName={fileName} onNewUpload={onNewUpload} />
      <div className="bulk-success-banner">
        <h3 className="bulk-success-title">Institution mapping report</h3>
        <p className="bulk-success-subtitle">Found {unmappedCount} unmapped institutions.</p>
      </div>
    </div>
  );
}

interface ResultsHeaderProps {
  fileName: string;
  resultsCount: number;
  onNewUpload: () => void;
}

export function ResultsHeader({ fileName, resultsCount, onNewUpload }: ResultsHeaderProps) {
  return (
    <div>
      <FileHeader fileName={fileName} onNewUpload={onNewUpload} />
      <div className="bulk-success-banner">
        <h3 className="bulk-success-title">Information successfully identified</h3>
        <p className="bulk-success-subtitle">
          We found {resultsCount} results from your document. Please review the extracted
          information and select the entries you want to submit to STAR.
        </p>
      </div>
    </div>
  );
}
