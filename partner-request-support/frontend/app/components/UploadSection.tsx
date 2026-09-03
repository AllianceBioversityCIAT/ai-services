'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Upload,
  Cloud,
  BarChart3,
  FileSpreadsheet,
  Info,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { partnerService } from '../services';
import { ApiPartnerRequest } from '../types';
import { ExcelPreviewModal } from './ExcelPreviewModal';

interface UploadSectionProps {
  file: File | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => File | null;
  processing: boolean;
  message: string;
  error: string | null;
  onUpload: () => void;
  apiPartners: ApiPartnerRequest[];
  batchSize: number;
  syncing: boolean;
  syncError: string | null;
  onSyncPartnerRequests: () => void;
  onProcessApiPartners: () => void;
  onClearCache: () => Promise<void>;
}

export const UploadSection = ({
  file,
  onFileChange,
  processing,
  message,
  error,
  onUpload,
  apiPartners,
  batchSize,
  syncing,
  syncError,
  onSyncPartnerRequests,
  onProcessApiPartners,
  onClearCache,
}: UploadSectionProps) => {
  const [uploadMode, setUploadMode] = useState<'excel' | 'api'>('excel');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const [clearCacheMessage, setClearCacheMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // The backend processes the oldest batchSize requests per run and reports that
  // size in the sync response; a backend that does not report it processes all.
  const batchCount = batchSize > 0 ? Math.min(batchSize, apiPartners.length) : apiPartners.length;
  const remainingAfterBatch = apiPartners.length - batchCount;

  const handleClearCacheConfirm = async () => {
    setClearingCache(true);
    try {
      await onClearCache();
      setClearCacheMessage({ type: 'success', text: 'Cache cleared. Next upload will reprocess all partners from scratch.' });
    } catch {
      setClearCacheMessage({ type: 'error', text: 'Failed to clear cache. Please try again.' });
    } finally {
      setClearingCache(false);
      setShowClearConfirm(false);
      setTimeout(() => setClearCacheMessage(null), 5000);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const blob = await partnerService.downloadTemplate();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'PartnerRequestTemplate_v1.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading template:', err);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div
        style={{
          background: 'white',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-md)',
          boxShadow: 'var(--shadow-md)',
          maxWidth: '700px',
          margin: '0 auto',
        }}
      >
        {/* Upload Header */}
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-md)' }}>
          <h2
            style={{
              fontSize: '1.25rem',
              fontWeight: 600,
              color: 'var(--cgiar-navy)',
              marginBottom: 'var(--space-xs)',
            }}
          >
            Process Partner Requests
          </h2>
          <p
            style={{
              fontSize: '0.875rem',
              color: 'var(--color-text-muted)',
            }}
          >
            Match partners with the CLARISA database using AI
          </p>
        </div>

        {/* Mode Selector */}
        <div
          style={{
            display: 'flex',
            gap: 'var(--space-sm)',
            marginBottom: 'var(--space-md)',
            background: 'var(--cgiar-light-gray)',
            padding: '4px',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <button
            onClick={() => setUploadMode('excel')}
            style={{
              flex: 1,
              padding: 'var(--space-sm)',
              background: uploadMode === 'excel' ? 'white' : 'transparent',
              color:
                uploadMode === 'excel' ? 'var(--cgiar-navy)' : 'var(--color-text-muted)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: uploadMode === 'excel' ? 'var(--shadow-sm)' : 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <Upload size={16} />
            Upload Excel
          </button>
          <button
            onClick={() => setUploadMode('api')}
            style={{
              flex: 1,
              padding: 'var(--space-sm)',
              background: uploadMode === 'api' ? 'white' : 'transparent',
              color: uploadMode === 'api' ? 'var(--cgiar-navy)' : 'var(--color-text-muted)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: uploadMode === 'api' ? 'var(--shadow-sm)' : 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <Cloud size={16} />
            API Requests {apiPartners.length > 0 && `(${apiPartners.length})`}
          </button>
        </div>

        {/* Excel Mode */}
        {uploadMode === 'excel' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {/* Upload Zone */}
            <div
              style={{
                border: `2px dashed ${file ? 'var(--cgiar-green)' : 'var(--cgiar-gray)'}`,
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-md)',
                textAlign: 'center',
                background: file ? '#F0F9E8' : 'var(--cgiar-light-gray)',
                transition: 'all 0.3s ease',
                cursor: 'pointer',
                marginBottom: 'var(--space-md)',
              }}
            >
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={onFileChange}
                style={{ display: 'none' }}
                id="file-upload"
              />
              <label htmlFor="file-upload" style={{ cursor: 'pointer', display: 'block' }}>
                <Upload
                  size={40}
                  style={{
                    color: file ? 'var(--cgiar-green)' : 'var(--color-text-muted)',
                    margin: '0 auto var(--space-sm)',
                  }}
                />
                {file ? (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <p
                      style={{
                        fontSize: '0.9375rem',
                        fontWeight: 600,
                        color: 'var(--cgiar-green)',
                        marginBottom: 'var(--space-xs)',
                      }}
                    >
                      {file.name}
                    </p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      Click to change file
                    </p>
                  </motion.div>
                ) : (
                  <div>
                    <p
                      style={{
                        fontSize: '0.9375rem',
                        fontWeight: 500,
                        color: 'var(--cgiar-navy)',
                        marginBottom: 'var(--space-xs)',
                      }}
                    >
                      Drop your Excel file here
                    </p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      or click to browse
                    </p>
                  </div>
                )}
              </label>
            </div>

            {/* Process Button */}
            <button
              onClick={() => setPreviewOpen(true)}
              disabled={!file || processing}
              style={{
                width: '100%',
                padding: 'var(--space-sm) var(--space-md)',
                background:
                  file && !processing
                    ? 'linear-gradient(135deg, var(--cgiar-green) 0%, #629600 100%)'
                    : 'var(--cgiar-gray)',
                color: file && !processing ? 'white' : 'var(--color-text-muted)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.9375rem',
                fontWeight: 600,
                cursor: file && !processing ? 'pointer' : 'not-allowed',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-sm)',
                border: 'none',
                boxShadow: file && !processing ? 'var(--shadow-md)' : 'none',
              }}
              onMouseOver={(e) => {
                if (file && !processing) e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseOut={(e) => {
                if (file && !processing) e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              {processing ? (
                <>
                  <div className="spinner" />
                  {message || 'Processing...'}
                </>
              ) : (
                <>
                  <BarChart3 size={18} />
                  Analyze Partners
                </>
              )}
            </button>

            {/* Recommendation Text */}
            <p
              style={{
                marginTop: 'var(--space-xs)',
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                textAlign: 'center',
                fontStyle: 'italic',
              }}
            >
              <strong>Recommendation:</strong> Upload a maximum of 10 partners in a single file
              for optimal processing.
            </p>

            {/* Info Box */}
            <div
              style={{
                marginTop: 'var(--space-md)',
                padding: 'var(--space-md)',
                background: '#E8F4FD',
                borderRadius: 'var(--radius-md)',
                borderLeft: '3px solid var(--cgiar-blue)',
              }}
            >
              <h4
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--cgiar-blue)',
                  marginBottom: 'var(--space-xs)',
                }}
              >
                Required Excel Format
              </h4>

              <ul
                style={{
                  paddingLeft: 'var(--space-md)',
                  color: 'var(--color-text-secondary)',
                  fontSize: '0.75rem',
                  lineHeight: 1.6,
                  marginBottom: 'var(--space-sm)',
                }}
              >
                <li>
                  <strong>Column 0:</strong> ID{' '}
                  <span style={{ color: '#DC2626', fontWeight: 600 }}>(required)</span>
                </li>
                <li>
                  <strong>Column 1:</strong> Partner Name{' '}
                  <span style={{ color: '#DC2626', fontWeight: 600 }}>(required)</span>
                </li>
                <li>
                  <strong>Column 2:</strong> Acronym (optional)
                </li>
                <li>
                  <strong>Column 3:</strong> Website (optional)
                </li>
                <li>
                  <strong>Column 4:</strong> Institution Type{' '}
                  <span style={{ color: '#DC2626', fontWeight: 600 }}>(required)</span>
                </li>
                <li>
                  <strong>Column 5:</strong> Country{' '}
                  <span style={{ color: '#DC2626', fontWeight: 600 }}>(required)</span>
                </li>
                <li>
                  <strong>Column 6:</strong> Category 1 (optional)
                </li>
                <li>
                  <strong>Column 7:</strong> Category 2 (optional)
                </li>
              </ul>

              {/* Download Template Button */}
              <button
                onClick={handleDownloadTemplate}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: 'var(--cgiar-blue)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = '#1e5a8e';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'var(--cgiar-blue)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <FileSpreadsheet size={14} />
                Download Excel Template
              </button>
            </div>
          </motion.div>
        )}

        {/* API Mode */}
        {uploadMode === 'api' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {/* API Status */}
            <div
              style={{
                background: syncing
                  ? '#F0F9E8'
                  : apiPartners.length > 0
                  ? '#E8F4FD'
                  : '#FEF3E8',
                border: `1px solid ${
                  syncing
                    ? 'var(--cgiar-green)'
                    : apiPartners.length > 0
                    ? 'var(--cgiar-blue)'
                    : 'var(--cgiar-yellow)'
                }`,
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-md)',
                marginBottom: 'var(--space-md)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 'var(--space-xs)',
                }}
              >
                <h4
                  style={{
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    color: 'var(--cgiar-navy)',
                  }}
                >
                  {syncing
                    ? 'Syncing...'
                    : apiPartners.length > 0
                    ? `${apiPartners.length} Pending Partner Requests`
                    : 'No Partner Requests'}
                </h4>
                <button
                  onClick={onSyncPartnerRequests}
                  disabled={syncing}
                  style={{
                    padding: '4px 10px',
                    background: 'white',
                    border: '1px solid var(--cgiar-gray)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    cursor: syncing ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    color: 'var(--cgiar-navy)',
                    transition: 'all 0.2s',
                  }}
                  onMouseOver={(e) => {
                    if (!syncing) e.currentTarget.style.background = 'var(--cgiar-light-gray)';
                  }}
                  onMouseOut={(e) => {
                    if (!syncing) e.currentTarget.style.background = 'white';
                  }}
                >
                  <RefreshCw
                    size={12}
                    style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }}
                  />
                  Refresh
                </button>
              </div>
              <p
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 1.5,
                }}
              >
                {syncing
                  ? 'Fetching partner requests from CLARISA API...'
                  : apiPartners.length === 0
                  ? 'Click Refresh to sync with CLARISA API'
                  : remainingAfterBatch > 0
                  ? `Ready to process the ${batchCount} oldest requests. The remaining ${remainingAfterBatch} stay queued for the next run.`
                  : `Ready to process all ${apiPartners.length} pending requests.`}
              </p>
            </div>

            {syncError && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  marginBottom: 'var(--space-md)',
                  padding: 'var(--space-sm)',
                  background: '#FEE',
                  border: '1px solid var(--color-error)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-error)',
                  fontSize: '0.75rem',
                }}
              >
                {syncError}
              </motion.div>
            )}

            {/* Process Button */}
            <button
              onClick={onProcessApiPartners}
              disabled={apiPartners.length === 0 || processing}
              style={{
                width: '100%',
                padding: 'var(--space-sm) var(--space-md)',
                background:
                  apiPartners.length > 0 && !processing
                    ? 'linear-gradient(135deg, var(--cgiar-blue) 0%, #0052A3 100%)'
                    : 'var(--cgiar-gray)',
                color:
                  apiPartners.length > 0 && !processing ? 'white' : 'var(--color-text-muted)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.9375rem',
                fontWeight: 600,
                cursor:
                  apiPartners.length > 0 && !processing ? 'pointer' : 'not-allowed',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-sm)',
                border: 'none',
                boxShadow:
                  apiPartners.length > 0 && !processing ? 'var(--shadow-md)' : 'none',
              }}
              onMouseOver={(e) => {
                if (apiPartners.length > 0 && !processing)
                  e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseOut={(e) => {
                if (apiPartners.length > 0 && !processing)
                  e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              {processing ? (
                <>
                  <div className="spinner" />
                  {message || 'Processing...'}
                </>
              ) : (
                <>
                  <BarChart3 size={18} />
                  {remainingAfterBatch > 0
                    ? `Process ${batchCount} Oldest Requests`
                    : 'Process Partner Requests'}
                </>
              )}
            </button>

            {/* Info Box */}
            <div
              style={{
                marginTop: 'var(--space-md)',
                padding: 'var(--space-md)',
                background: '#FFF4E6',
                borderRadius: 'var(--radius-md)',
                borderLeft: '3px solid var(--cgiar-yellow)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'start', gap: 'var(--space-xs)' }}>
                <Info
                  size={16}
                  style={{
                    color: 'var(--cgiar-yellow)',
                    marginTop: '2px',
                    flexShrink: 0,
                  }}
                />
                <div>
                  <h4
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: 'var(--cgiar-navy)',
                      marginBottom: '4px',
                    }}
                  >
                    Batch Processing
                  </h4>
                  <p
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--color-text-secondary)',
                      lineHeight: 1.5,
                      margin: 0,
                    }}
                  >
                    Requests are processed in batches, oldest first, to stay within the
                    processing time limit. Accept or reject each one in CLARISA and hit
                    Refresh: resolved requests leave the queue and the next batch moves up.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        <ExcelPreviewModal
          isOpen={previewOpen}
          file={file}
          onClose={() => setPreviewOpen(false)}
          onContinue={onUpload}
        />

        {/* Clear Cache Button */}
        <div style={{ marginTop: 'var(--space-md)', textAlign: 'center' }}>
          <button
            onClick={() => setShowClearConfirm(true)}
            disabled={processing || clearingCache}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-text-muted)',
              fontSize: '0.75rem',
              cursor: processing || clearingCache ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              transition: 'color 0.2s',
              textDecoration: 'underline',
              textDecorationStyle: 'dotted',
            }}
            onMouseOver={(e) => { if (!processing && !clearingCache) e.currentTarget.style.color = 'var(--color-error)'; }}
            onMouseOut={(e) => { e.currentTarget.style.color = 'var(--color-text-muted)'; }}
          >
            <Trash2 size={12} />
            Clear result cache
          </button>
        </div>

        {/* Clear Cache Feedback */}
        {clearCacheMessage && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              marginTop: 'var(--space-sm)',
              padding: 'var(--space-sm) var(--space-md)',
              background: clearCacheMessage.type === 'success' ? '#F0F9E8' : '#FEF2F2',
              border: `1px solid ${clearCacheMessage.type === 'success' ? 'var(--cgiar-green)' : '#FCA5A5'}`,
              borderRadius: 'var(--radius-md)',
              color: clearCacheMessage.type === 'success' ? 'var(--cgiar-green)' : '#991B1B',
              fontSize: '0.8125rem',
              textAlign: 'center',
            }}
          >
            {clearCacheMessage.text}
          </motion.div>
        )}

        {/* Clear Cache Confirm Modal */}
        {showClearConfirm && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.45)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 9999,
            }}
            onClick={() => !clearingCache && setShowClearConfirm(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{
                background: 'white',
                borderRadius: 'var(--radius-xl)',
                padding: 'var(--space-lg)',
                maxWidth: '420px',
                width: '90%',
                boxShadow: 'var(--shadow-xl)',
                textAlign: 'center',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  background: '#FEF2F2',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto var(--space-md)',
                }}
              >
                <Trash2 size={22} style={{ color: 'var(--color-error)' }} />
              </div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--cgiar-navy)', marginBottom: 'var(--space-xs)' }}>
                Clear Result Cache?
              </h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', lineHeight: 1.5, marginBottom: 'var(--space-md)' }}>
                All cached matching results will be deleted. The next time you upload an Excel file,
                every partner will be reprocessed from scratch. This cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: 'var(--space-sm)', justifyContent: 'center' }}>
                <button
                  onClick={() => setShowClearConfirm(false)}
                  disabled={clearingCache}
                  style={{
                    padding: 'var(--space-sm) var(--space-md)',
                    background: 'var(--cgiar-light-gray)',
                    color: 'var(--cgiar-navy)',
                    border: '1px solid var(--cgiar-gray)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    cursor: clearingCache ? 'not-allowed' : 'pointer',
                    minWidth: '100px',
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleClearCacheConfirm}
                  disabled={clearingCache}
                  style={{
                    padding: 'var(--space-sm) var(--space-md)',
                    background: clearingCache ? 'var(--cgiar-gray)' : 'var(--color-error)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    cursor: clearingCache ? 'not-allowed' : 'pointer',
                    minWidth: '100px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                  }}
                >
                  {clearingCache ? (
                    <><div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} /> Clearing...</>
                  ) : (
                    <><Trash2 size={14} /> Clear Cache</>
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              marginTop: 'var(--space-md)',
              padding: 'var(--space-md)',
              background: '#FEF2F2',
              border: '1px solid #FCA5A5',
              borderRadius: 'var(--radius-md)',
              color: '#991B1B',
              fontSize: '0.875rem',
            }}
          >
            {error}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};
