'use client';

import { FileHeader } from './FileHeader';

// Hoisted static JSX (rendering-hoist-jsx)
const InfoBanner = (
  <div className="bulk-info-banner">
    <div className="bulk-info-icon">i</div>
    <div className="bulk-info-text">
      This module is currently part of a pilot phase, where the process is being tested with a limited and controlled group of users, specifically Admins and MEL Focal Points, in close collaboration with the STAR technical team. It uses AI-powered processing to extract and map information, so all results should be carefully reviewed before submission to ensure accuracy.
    </div>
  </div>
);

interface UploadHeaderProps {
  userName?: { firstName: string; lastName: string } | null;
}

export function UploadHeader({ userName }: UploadHeaderProps) {
  return (
    <div>
      <div className="bulk-content-header">
        <h1 className="bulk-page-title">Upload multiple Capacity Development entries within a specific bilateral</h1>
        {userName && (
          <div className="bulk-welcome">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span className="bulk-welcome-label">Welcome,</span>
            <span className="bulk-welcome-name">{userName.firstName} {userName.lastName}</span>
          </div>
        )}
      </div>
      {InfoBanner}
    </div>
  );
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
        <h3 className="bulk-success-title">Information successfully identified</h3>
        <div className="bulk-info-banner">
          <div className="bulk-info-icon">i</div>
          <div className="bulk-info-text">
            This module is currently part of a pilot phase, where the process is being tested with a limited and controlled group of users, specifically Admins and MEL Focal Points, in close collaboration with the STAR technical team. It uses AI-powered processing to extract and map information, so all results should be carefully reviewed before submission to ensure accuracy.
          </div>
        </div>
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
        <div className="bulk-info-banner">
          <div className="bulk-info-icon">i</div>
          <div className="bulk-info-text">
            This module is currently part of a pilot phase, where the process is being tested with a limited and controlled group of users, specifically Admins and MEL Focal Points, in close collaboration with the STAR technical team. It uses AI-powered processing to extract and map information, so all results should be carefully reviewed before submission to ensure accuracy.
          </div>
        </div>
      </div>
    </div>
  );
}
