'use client';

import { useState, useCallback, useEffect } from 'react';
import type { BulkUploadResult, RecordStatus, DocSource, AppStep, UnmappedInstitution, SummaryRecord } from './types';
import { useBulkUploadApi } from './hooks/useBulkUploadApi';
import { useTableFilters } from './hooks/useTableFilters';
import { useTableSort } from './hooks/useTableSort';
import { useNavigationGuard } from './hooks/useNavigationGuard';
import { loadRecordStatuses } from './hooks/useDynamoDB';
import { extractUnmappedInstitutions } from './utils/dataFormatters';
import { createUnmappedReportCSV, downloadCSV } from './utils/csvUtils';
import { setNestedValue } from './utils/tableHelpers';
import { checkCompleteness } from './utils/completenessChecker';

import { LoadingOverlay } from './components/LoadingOverlay';
import { ErrorMessage } from './components/ErrorMessage';
import { UploadHeader, UnmappedHeader, ResultsHeader } from './components/Headers';
import { StepIndicator } from './components/StepIndicator';
import { Step1Upload } from './components/Step1Upload';
import { UnmappedTable } from './components/UnmappedTable';
import { ResultsTable } from './components/ResultsTable';
import { Step4Summary } from './components/Step4Summary';

import deniedAccessImage from '../../public/static/bulk_upload/denied_access.png';

export default function BulkUploadModule() {
  // ── Auth ──────────────────────────────────────────────
  const [authStatus, setAuthStatus] = useState<'loading' | 'valid' | 'invalid'>('loading');
  const [userToken, setUserToken] = useState<string | null>(null);
  const [userName, setUserName] = useState<{ firstName: string; lastName: string } | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [starUserId, setStarUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userFullName, setUserFullName] = useState<string | null>(null);

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
      .then((res) => res.json() as Promise<{ valid: boolean; firstName?: string; lastName?: string; email?: string | null; userId?: string | null }>)
      .then((data) => {
        if (data.valid) {
          setUserToken(token);
          setUserName({ firstName: data.firstName ?? '', lastName: data.lastName ?? '' });
          setUserEmail(data.email ?? null);
          setStarUserId(data.userId ?? null);
          // Prefer email as the user identifier for interaction tracking, fall back to userId
          setUserId(data.email ?? data.userId ?? null);
          setUserFullName([data.firstName, data.lastName].filter(Boolean).join(' ') || null);
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
  const [currentInteractionId, setCurrentInteractionId] = useState<string | null>(null);
  const [editedIds, setEditedIds] = useState<Set<string>>(new Set());
  const [recordStatuses, setRecordStatuses] = useState<Record<string, RecordStatus>>({});
  const [unmappedInstitutions, setUnmappedInstitutions] = useState<UnmappedInstitution[]>([]);
  const [submissionSummary, setSubmissionSummary] = useState<{
    approved: SummaryRecord[];
    draft: SummaryRecord[];
    failed: SummaryRecord[];
  } | null>(null);

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
  const api = useBulkUploadApi(userToken, userId, userFullName);

  // ── Filters & Sort ───────────────────────────────────
  const filters = useTableFilters();
  const sort = useTableSort();

  // ── Derived: filtered + sorted results ──
  const filteredResults = filters.applyFilters(editedData, recordStatuses);
  const displayResults = sort.applySort(filteredResults, recordStatuses);

  const hasWorkInProgress = step !== 'upload' || api.isLoading;
  useNavigationGuard(hasWorkInProgress);

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
    setSubmissionSummary(null);
    setCurrentInteractionId(null);
    setEditedIds(new Set());
    filters.clearAllFilters();
    sort.clearAllSorts();
  }, [filters, sort]);

  const handleFinishProcess = useCallback(() => {
    handleNewUpload();
  }, [handleNewUpload]);

  const handleProcessSuccess = useCallback(
    (results: BulkUploadResult[], statuses: Record<string, RecordStatus>, fileName: string, interactionId: string | null) => {
      const unmapped = extractUnmappedInstitutions(results);
      const cloned = JSON.parse(JSON.stringify(results)) as BulkUploadResult[];
      setCurrentResults(results);
      setEditedData(cloned);
      setUnmappedInstitutions(unmapped);
      setRecordStatuses(statuses);
      setCurrentFileName(fileName);
      setCurrentInteractionId(interactionId);
      setEditedIds(new Set());
      filters.clearAllFilters();
      sort.clearAllSorts();
      setSelectedIndices(new Set());
      setStep('results');
    },
    [filters, sort],
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
    const recordId = editedData[globalIdx]?.id;
    setEditedData((prev) => {
      const next = [...prev];
      const updated = { ...next[globalIdx] } as BulkUploadResult;
      setNestedValue(updated, field, value);
      next[globalIdx] = updated;
      return next;
    });
    if (recordId != null) {
      setEditedIds((prev) => {
        const next = new Set(prev);
        next.add(String(recordId));
        return next;
      });
    }
  }, [editedData]);

  const handleStatusUpdate = useCallback((newStatuses: Record<string, RecordStatus>) => {
    setRecordStatuses((prev) => ({ ...prev, ...newStatuses }));
  }, []);

  const handleSubmitToStar = useCallback(() => {
    if (!api.authToken || !currentFileName) return;
    const selected = Array.from(selectedIndices)
      .map((idx) => editedData[idx])
      .filter((result) => recordStatuses[String(result.id)]?.status !== 'complete');
    if (selected.length === 0) return;
    api.submitToSTAR(selected, currentFileName, api.authToken, (completeIds, newStatuses) => {
      setRecordStatuses((prev) => ({ ...prev, ...newStatuses }));
      // Build summary from this session only
      const approved: SummaryRecord[] = [];
      const draft: SummaryRecord[] = [];
      const failed: SummaryRecord[] = [];
      for (const r of selected) {
        const rid = String(r.id);
        const status = newStatuses[rid];
        if (!status) continue;
        const record: SummaryRecord = {
          id: rid,
          title: r.title,
          contract_code: r.contract_code,
          result_official_code: status.link?.split('/result/').pop(),
          star_link: status.link ?? undefined,
          submission_status: status.status === 'complete'
            ? (completeIds.has(rid) ? 'approved' : 'draft')
            : 'failed',
          error_message: status.errorMessage,
          rawData: r,
        };
        if (record.submission_status === 'approved') approved.push(record);
        else if (record.submission_status === 'draft') draft.push(record);
        else failed.push(record);
      }
      setSubmissionSummary({ approved, draft, failed });
      setSelectedIndices(new Set());
      setEditedData((prev) => [...prev]);
    }, currentInteractionId, editedIds);
  }, [api, currentFileName, selectedIndices, editedData, recordStatuses, currentInteractionId, editedIds]);

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
      {step === 'upload' && <UploadHeader userName={userName} />}
      {step === 'unmapped' && currentFileName !== null && (
        <UnmappedHeader
          fileName={currentFileName}
          unmappedCount={unmappedInstitutions.length}
          onNewUpload={handleNewUpload}
        />
      )}
      {(step === 'results' || step === 'summary') && currentFileName !== null && (
        <ResultsHeader
          fileName={currentFileName}
          resultsCount={currentResults.length}
          onNewUpload={handleNewUpload}
        />
      )}

      {/* White card container */}
      <div className="bulk-upload-container">
        {/* Step indicator — inside white card */}
        <StepIndicator currentStep={step} />

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
            authToken={userToken}
            userEmail={userEmail}
            starUserId={starUserId}
            userFullName={userFullName}
            onDownloadReport={handleDownloadUnmappedReport}
            onBackToResults={handleNextStep}
            onGoToSummary={() => setStep('summary')}
          />
        )}

        {step === 'summary' && currentFileName !== null && (
          <Step4Summary
            approved={submissionSummary?.approved ?? []}
            draft={submissionSummary?.draft ?? []}
            failed={submissionSummary?.failed ?? []}
            fileName={currentFileName}
            userId={userId}
            interactionId={currentInteractionId}
            onBackToUnmapped={() => setStep('unmapped')}
            onFinishProcess={handleFinishProcess}
          />
        )}

        {step === 'results' && (
          <ResultsTable
            results={currentResults}
            editedData={editedData}
            recordStatuses={recordStatuses}
            activeFilters={filters.activeFilters}
            activeSort={sort.activeSort}
            currentTab={filters.currentTab}
            filteredResults={displayResults}
            selectedIndices={selectedIndices}
            onEdit={handleCellEdit}
            onSelectionChange={setSelectedIndices}
            onFilterApply={filters.setFilter}
            onFilterClear={filters.clearFilter}
            onSortApply={sort.setSort}
            onSortClear={sort.clearSort}
            onTabChange={(tab) => {
              filters.setTab(tab);
              sort.setTab(tab);
              setSelectedIndices(new Set());
            }}
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
