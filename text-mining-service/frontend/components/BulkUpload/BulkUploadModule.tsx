'use client';

import { useState, useCallback, useEffect } from 'react';
import type { BulkUploadResult, RecordStatus, DocSource, AppStep, UnmappedInstitution } from './types';
import { useBulkUploadApi } from './hooks/useBulkUploadApi';
import { useTableFilters } from './hooks/useTableFilters';
import { loadRecordStatuses } from './hooks/useDynamoDB';
import { extractUnmappedInstitutions } from './utils/dataFormatters';
import { createUnmappedReportCSV, createDraftReportCSV, downloadCSV } from './utils/csvUtils';
import { setNestedValue } from './utils/tableHelpers';
import { checkCompleteness } from './utils/completenessChecker';

import { LoadingOverlay } from './components/LoadingOverlay';
import { ErrorMessage } from './components/ErrorMessage';
import { UploadHeader, UnmappedHeader, ResultsHeader } from './components/Headers';
import { StepIndicator } from './components/StepIndicator';
import { Step1Upload } from './components/Step1Upload';
import { UnmappedTable } from './components/UnmappedTable';
import { ResultsTable } from './components/ResultsTable';

import deniedAccessImage from '../../public/static/bulk_upload/denied_access.png';

export default function BulkUploadModule() {
  // ── Auth ──────────────────────────────────────────────
  const [authStatus, setAuthStatus] = useState<'loading' | 'valid' | 'invalid'>('loading');
  const [userToken, setUserToken] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('access_token');
    // Strip the token from the URL immediately to avoid it lingering in browser history
    window.history.replaceState({}, '', window.location.pathname);

    if (!token) {
      setAuthStatus('invalid');
      return;
    }

    fetch('/api/validate-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then((res) => res.json() as Promise<{ valid: boolean }>)
      .then((data) => {
        if (data.valid) {
          setUserToken(token);
          setAuthStatus('valid');
        } else {
          setAuthStatus('invalid');
        }
      })
      .catch(() => setAuthStatus('invalid'));
  }, []);

  // ── Scroll to top on page load ────────────────────────
  useEffect(() => {
    if (typeof window !== 'undefined') {
      history.scrollRestoration = 'manual';
      window.scrollTo(0, 0);
    }
  }, []);

  // ── App Step ──────────────────────────────────────────
  const [step, setStep] = useState<AppStep>('upload');

  // ── File State ────────────────────────────────────────
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // ── Results State ─────────────────────────────────────
  const [currentResults, setCurrentResults] = useState<BulkUploadResult[]>([]);
  const [editedData, setEditedData] = useState<BulkUploadResult[]>([]);
  const [currentFileName, setCurrentFileName] = useState<string | null>(null);
  const [recordStatuses, setRecordStatuses] = useState<Record<string, RecordStatus>>({});
  const [unmappedInstitutions, setUnmappedInstitutions] = useState<UnmappedInstitution[]>([]);

  // ── Selection State ───────────────────────────────────
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());

  // ── Reprocess Modal State ────────────────────────────
  const [reprocessModalData, setReprocessModalData] = useState<{
    mode: DocSource;
    file: File | null;
    s3Key: string | null;
    fileName: string;
    completeCount: number;
    failedCount: number;
  } | null>(null);

  // ── API ───────────────────────────────────────────────
  const api = useBulkUploadApi(userToken);

  // ── Filters ───────────────────────────────────────────
  const filters = useTableFilters();

  // ── Derived: filtered results (rerender-derived-state-no-effect) ──
  const filteredResults = filters.applyFilters(editedData, recordStatuses);

  // ══════════════════════════════════════════
  // Handlers
  // ══════════════════════════════════════════

  const handleFileSelect = useCallback((file: File) => setSelectedFile(file), []);
  const handleFileRemove = useCallback(() => setSelectedFile(null), []);

  const handleNewUpload = useCallback(() => {
    setStep('upload');
    setSelectedFile(null);
    setCurrentResults([]);
    setEditedData([]);
    setUnmappedInstitutions([]);
    setRecordStatuses({});
    setSelectedIndices(new Set());
    filters.clearAllFilters();
  }, [filters]);

  const handleFinishProcess = useCallback(() => {
    const draftResults = editedData.filter(
      (r) =>
        recordStatuses[String(r.id)]?.status === 'complete' &&
        !checkCompleteness(r).isComplete,
    );
    if (draftResults.length > 0) {
      const csv = createDraftReportCSV(draftResults, recordStatuses);
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const baseName = currentFileName?.replace(/\.[^.]+$/, '') ?? 'draft_results';
      downloadCSV(csv, `draft_report_${baseName}_${timestamp}.csv`);
    }
    handleNewUpload();
  }, [editedData, recordStatuses, currentFileName, handleNewUpload]);

  const handleProcessSuccess = useCallback(
    (results: BulkUploadResult[], statuses: Record<string, RecordStatus>, fileName: string) => {
      const unmapped = extractUnmappedInstitutions(results);
      const cloned = JSON.parse(JSON.stringify(results)) as BulkUploadResult[];
      setCurrentResults(results);
      setEditedData(cloned);
      setUnmappedInstitutions(unmapped);
      setRecordStatuses(statuses);
      setCurrentFileName(fileName);
      filters.clearAllFilters();
      setSelectedIndices(new Set());
      setStep('results');
    },
    [filters],
  );

  const handleProcess = useCallback(
    async (mode: DocSource, file: File | null, s3Key: string | null) => {
      const fileName =
        mode === 'upload' ? (file?.name ?? '') : (s3Key?.split('/').pop() ?? s3Key ?? '');
      const savedStatuses = await loadRecordStatuses(fileName);
      const completeCount = savedStatuses.complete?.length ?? 0;
      const failedCount = savedStatuses.failed?.length ?? 0;
      if (completeCount > 0 || failedCount > 0) {
        setReprocessModalData({ mode, file, s3Key, fileName, completeCount, failedCount });
        return;
      }
      api.processDocument(mode, file, s3Key, handleProcessSuccess);
    },
    [api, handleProcessSuccess],
  );

  const handleConfirmReprocess = useCallback(() => {
    if (!reprocessModalData) return;
    const { mode, file, s3Key } = reprocessModalData;
    setReprocessModalData(null);
    api.processDocument(mode, file, s3Key, handleProcessSuccess);
  }, [reprocessModalData, api, handleProcessSuccess]);

  const handleCancelReprocess = useCallback(() => {
    setReprocessModalData(null);
  }, []);

  const handleNextStep = useCallback(() => setStep('results'), []);
  const handleViewUnmapped = useCallback(() => setStep('unmapped'), []);

  const handleDownloadUnmappedReport = useCallback(() => {
    if (unmappedInstitutions.length === 0) return;
    const csv = createUnmappedReportCSV(unmappedInstitutions);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    downloadCSV(csv, `unmapped_institutions_${timestamp}.csv`);
  }, [unmappedInstitutions]);

  const handleCellEdit = useCallback((globalIdx: number, field: string, value: unknown) => {
    setEditedData((prev) => {
      const next = [...prev];
      const updated = { ...next[globalIdx] } as BulkUploadResult;
      setNestedValue(updated, field, value);
      next[globalIdx] = updated;
      return next;
    });
  }, []);

  const handleStatusUpdate = useCallback((newStatuses: Record<string, RecordStatus>) => {
    setRecordStatuses((prev) => ({ ...prev, ...newStatuses }));
  }, []);

  const handleSubmitToStar = useCallback(() => {
    if (!api.authToken || !currentFileName) return;
    const selected = Array.from(selectedIndices)
      .map((idx) => editedData[idx])
      .filter((result) => recordStatuses[String(result.id)]?.status !== 'complete');
    if (selected.length === 0) return;
    api.submitToSTAR(selected, currentFileName, api.authToken, handleStatusUpdate, () => {
      setSelectedIndices(new Set());
      setEditedData((prev) => [...prev]);
    });
  }, [api, currentFileName, selectedIndices, editedData, handleStatusUpdate, recordStatuses]);

  const handleClearSelections = useCallback(() => {
    setSelectedIndices(new Set());
  }, []);

  // ── Auth gate ─────────────────────────────────────────
  if (authStatus === 'loading') {
    return (
      <div className="bulk-upload-wrapper">
        <div className="bulk-upload-container">
          <LoadingOverlay text="Verifying access..." />
        </div>
      </div>
    );
  }

  if (authStatus === 'invalid') {
    return (
      <div className="bulk-upload-wrapper">
        <div className="bulk-upload-container">
          <div className="bulk-auth-denied">
            <div className="bulk-auth-denied-icon">
              <img
                src={deniedAccessImage.src}
                alt="Access denied"
                width={deniedAccessImage.width}
                height={deniedAccessImage.height}
                className="bulk-auth-denied-image"
              />
            </div>
            <h2 className="bulk-auth-denied-title">Access Denied</h2>
            <p className="bulk-auth-denied-message">
              You don&apos;t have the necessary permissions to access the Bulk Upload tool.
              Please contact your administrator if you believe this is a mistake.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bulk-upload-wrapper">
      {/* Step-contextual headers */}
      {step === 'upload' && <UploadHeader />}
      {step === 'unmapped' && currentFileName !== null && (
        <UnmappedHeader
          fileName={currentFileName}
          unmappedCount={unmappedInstitutions.length}
          onNewUpload={handleNewUpload}
        />
      )}
      {step === 'results' && currentFileName !== null && (
        <ResultsHeader
          fileName={currentFileName}
          resultsCount={currentResults.length}
          onNewUpload={handleNewUpload}
        />
      )}

      {/* Step indicator — outside white card, in header background */}
      <StepIndicator currentStep={step} />

      {/* White card container */}
      <div className="bulk-upload-container">
        {api.isLoading && <LoadingOverlay text={api.loadingText} />}

        {step === 'upload' && (
          <Step1Upload
            selectedFile={selectedFile}
            s3Objects={api.s3Objects}
            onFileSelect={handleFileSelect}
            onFileRemove={handleFileRemove}
            onProcess={handleProcess}
            onLoadS3Objects={api.loadS3Objects}
            onDownloadTemplate={api.downloadTemplate}
          />
        )}

        {step === 'unmapped' && (
          <UnmappedTable
            institutions={unmappedInstitutions}
            onDownloadReport={handleDownloadUnmappedReport}
            onBackToResults={handleNextStep}
            onFinishProcess={handleFinishProcess}
          />
        )}

        {step === 'results' && (
          <ResultsTable
            results={currentResults}
            editedData={editedData}
            recordStatuses={recordStatuses}
            activeFilters={filters.activeFilters}
            currentTab={filters.currentTab}
            filteredResults={filteredResults}
            selectedIndices={selectedIndices}
            onEdit={handleCellEdit}
            onSelectionChange={setSelectedIndices}
            onFilterApply={filters.setFilter}
            onFilterClear={filters.clearFilter}
            onTabChange={(tab) => { filters.setTab(tab); setSelectedIndices(new Set()); }}
            onSubmitToStar={handleSubmitToStar}
            onClearSelections={handleClearSelections}
            onViewUnmapped={handleViewUnmapped}
            starSubmissionResponse={api.starSubmissionResponse}
            authToken={api.authToken}
          />
        )}
      </div>

      {/* Error message (outside white card) */}
      {api.errorMessage !== null && <ErrorMessage message={api.errorMessage} />}

      {/* Reprocess confirmation modal */}
      {reprocessModalData !== null && (
        <div className="bulk-confirm-overlay">
          <div className="bulk-confirm-modal">
            <div className="bulk-confirm-icon">⚠️</div>
            <h2 className="bulk-confirm-title">File already processed</h2>
            <p className="bulk-confirm-desc">
              <strong>{reprocessModalData.fileName}</strong> has been processed before.
              {reprocessModalData.completeCount > 0 && (
                <> {reprocessModalData.completeCount} record{reprocessModalData.completeCount !== 1 ? 's were' : ' was'} submitted to STAR.</>
              )}
              {reprocessModalData.failedCount > 0 && (
                <> {reprocessModalData.failedCount} record{reprocessModalData.failedCount !== 1 ? 's' : ''} previously failed.</>              )}
            </p>
            <p className="bulk-confirm-sub">
              If you continue, the file will be re-processed by the AI and previous submission statuses will be reloaded.
              Make sure this file contains the same data — reusing a file name with different records may cause tracking issues.
            </p>
            <div className="bulk-confirm-actions">
              <button className="bulk-confirm-btn-cancel" onClick={handleCancelReprocess}>
                Cancel
              </button>
              <button className="bulk-confirm-btn-submit" onClick={handleConfirmReprocess}>
                Yes, re-process
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
