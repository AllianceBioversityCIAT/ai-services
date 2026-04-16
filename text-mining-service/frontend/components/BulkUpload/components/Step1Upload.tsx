'use client';

import { useState, useCallback } from 'react';
import type { DocSource } from '../types';
import { FileDropzone } from './FileDropzone';
import { S3FileSelector } from './S3FileSelector';

import uploadFileIcon from '../../../public/static/bulk_upload/upload_file.png';
import previousFileIcon from '../../../public/static/bulk_upload/previous_file.png';

// Hoisted static SVGs (rendering-hoist-jsx)
const DownloadSvg = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <path d="M8 12L3 7h3V2h4v5h3L8 12z" />
    <rect y="14" width="16" height="2" />
  </svg>
);

const ChevronSvg = (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" style={{ marginLeft: 4 }} aria-hidden>
    <path d="M6 9L2 5h8L6 9z" />
  </svg>
);

const ProcessArrowSvg = (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
    <path d="M10 4l6 6-6 6V4z" />
  </svg>
);

// Hoisted static guidelines list (rendering-hoist-jsx)
const GuidelinesList = (
  <ul className="bulk-requirements-list">
    <li className="bulk-note-tip"><strong>💡 Tip</strong> → Upload all records in a single Excel file to avoid running the process multiple times.</li>
    <li><strong>File name</strong> → Use a distinctive name (e.g., your name or date) to easily identify it.</li>
    <li><strong>Column names</strong> → Follow the template to ensure accurate AI mapping. Remember to add an <strong>ID column</strong> with incremental numbers.</li>
    <li><strong>Recommendation</strong> → Upload files with a maximum of <strong>100 rows</strong> to ensure optimal performance and avoid processing issues.</li>
    <li className="bulk-note-warning"><strong>⚠️ Warning</strong> → Do not reuse the same file name for different datasets, as this may affect tracking and processing.</li>
  </ul>
);

interface Step1UploadProps {
  selectedFile: File | null;
  s3Objects: string[];
  onFileSelect: (file: File) => void;
  onFileRemove: () => void;
  onProcess: (mode: DocSource, file: File | null, s3Key: string | null) => void;
  onLoadS3Objects: (prefix?: string) => void;
  onDownloadTemplate: (lang: 'es' | 'en') => void;
}

export function Step1Upload({
  selectedFile,
  s3Objects,
  onFileSelect,
  onFileRemove,
  onProcess,
  onLoadS3Objects,
  onDownloadTemplate,
}: Step1UploadProps) {
  const [docSource, setDocSource] = useState<DocSource | 'previous'>('upload');
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [s3Prefix, setS3Prefix] = useState('');
  const [selectedS3Key, setSelectedS3Key] = useState('');

  const handleSourceChange = useCallback(
    (value: DocSource | 'previous') => {
      setDocSource(value);
      if (value === 's3' && s3Objects.length === 0) {
        onLoadS3Objects();
      }
    },
    [s3Objects.length, onLoadS3Objects],
  );

  const handleS3KeyChange = useCallback((key: string) => {
    setSelectedS3Key(key);
  }, []);

  const handleProcess = useCallback(() => {
    if (docSource === 'upload') {
      onProcess('upload', selectedFile, null);
    } else {
      onProcess('s3' as DocSource, null, selectedS3Key || (s3Objects[0] ?? null));
    }
  }, [docSource, selectedFile, selectedS3Key, s3Objects, onProcess]);

  const toggleDownload = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDownloadOpen((prev) => !prev);
  }, []);

  const handleDownload = useCallback(
    (lang: 'es' | 'en') => {
      setDownloadOpen(false);
      onDownloadTemplate(lang);
    },
    [onDownloadTemplate],
  );

  // Derived: can process? (rerender-derived-state-no-effect)
  const canProcess = docSource === 'upload' ? selectedFile !== null : s3Objects.length > 0;
  const isS3Mode = docSource !== 'upload';

  return (
    <div className="bulk-step">
      <h2 className="bulk-section-title">Document source</h2>

      {/* Source Selection Cards */}
      <div className="bulk-source-cards">
        <label className={`bulk-source-card${docSource === 'upload' ? ' selected' : ''}`}>
          <input
            type="radio"
            name="bulkDocSource"
            value="upload"
            checked={docSource === 'upload'}
            onChange={() => handleSourceChange('upload' as DocSource)}
          />
          <div className="bulk-card-icon">
            <img
              src={uploadFileIcon.src}
              alt="Upload file icon"
              width={60}
              height={60}
            />
          </div>
          <div className="bulk-card-title">UPLOAD FILE</div>
          <div className="bulk-card-description">Upload from your computer.</div>
          <div className="bulk-radio-indicator" />
        </label>

        <label className={`bulk-source-card${docSource !== 'upload' ? ' selected' : ''}`}>
          <input
            type="radio"
            name="bulkDocSource"
            value="previous"
            checked={docSource !== 'upload'}
            onChange={() => handleSourceChange('s3' as DocSource)}
          />
          <div className="bulk-card-icon">
            <img
              src={previousFileIcon.src}
              alt="Previous file icon"
              width={60}
              height={60}
            />
          </div>
          <div className="bulk-card-title">PREVIOUS FILE</div>
          <div className="bulk-card-description">Choose from saved files.</div>
          <div className="bulk-radio-indicator" />
        </label>
      </div>

      {/* Guidelines (only in upload mode) */}
      {!isS3Mode && (
        <div className="bulk-guidelines-section">
          <div className="bulk-guidelines-header">
            <span className="bulk-guidelines-title">EXCEL TEMPLATE &amp; GUIDELINES</span>
            <div className="bulk-download-dropdown">
              <button className="bulk-download-guide-btn" type="button" onClick={toggleDownload}>
                {DownloadSvg}
                Download guide
                {ChevronSvg}
              </button>
              {downloadOpen && (
                <div className="bulk-download-options">
                  <button className="bulk-download-option" type="button" onClick={() => handleDownload('es')}>
                    🇪🇸 Spanish
                  </button>
                  <button className="bulk-download-option" type="button" onClick={() => handleDownload('en')}>
                    🇬🇧 English
                  </button>
                </div>
              )}
            </div>
          </div>
          {GuidelinesList}
        </div>
      )}

      {/* Upload / S3 modes */}
      {!isS3Mode ? (
        <div>
          <h3 className="bulk-subsection-title">Upload file</h3>
          <FileDropzone
            selectedFile={selectedFile}
            onFileSelect={onFileSelect}
            onFileRemove={onFileRemove}
          />
        </div>
      ) : (
        <S3FileSelector
          s3Objects={s3Objects}
          selectedKey={selectedS3Key}
          prefix={s3Prefix}
          onPrefixChange={setS3Prefix}
          onSelectedKeyChange={handleS3KeyChange}
          onRefresh={onLoadS3Objects}
        />
      )}

      {/* Process button */}
      <div className="bulk-actions">
        <button
          className="bulk-btn-process"
          type="button"
          disabled={!canProcess}
          onClick={handleProcess}
        >
          Process document
          {ProcessArrowSvg}
        </button>
      </div>
    </div>
  );
}
