'use client';

import { useState, useCallback } from 'react';
import type { BulkUploadResult, RecordStatus, DocSource, AppStep, UnmappedInstitution } from './types';
import { useBulkUploadApi } from './hooks/useBulkUploadApi';
import { useTableFilters } from './hooks/useTableFilters';
import { extractUnmappedInstitutions } from './utils/dataFormatters';
import { createUnmappedReportCSV, downloadCSV } from './utils/csvUtils';
import { setNestedValue } from './utils/tableHelpers';

import { LoadingOverlay } from './components/LoadingOverlay';
import { ErrorMessage } from './components/ErrorMessage';
import { UploadHeader, UnmappedHeader, ResultsHeader } from './components/Headers';
import { Step1Upload } from './components/Step1Upload';
import { UnmappedTable } from './components/UnmappedTable';
import { ResultsTable } from './components/ResultsTable';

export default function BulkUploadModule() {
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

  // ── API ───────────────────────────────────────────────
  const api = useBulkUploadApi();

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

  const handleProcess = useCallback(
    (mode: DocSource, file: File | null, s3Key: string | null) => {
      api.processDocument(mode, file, s3Key, (results, statuses, fileName) => {
        const unmapped = extractUnmappedInstitutions(results);
        const cloned = JSON.parse(JSON.stringify(results)) as BulkUploadResult[];
        setCurrentResults(results);
        setEditedData(cloned);
        setUnmappedInstitutions(unmapped);
        setRecordStatuses(statuses);
        setCurrentFileName(fileName);
        filters.clearAllFilters();
        setSelectedIndices(new Set());
        setStep('unmapped');
      });
    },
    [api, filters],
  );

  const handleNextStep = useCallback(() => setStep('results'), []);

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
    const selected = Array.from(selectedIndices).map((idx) => editedData[idx]);
    api.submitToSTAR(selected, currentFileName, api.authToken, handleStatusUpdate, () => {
      setEditedData((prev) => [...prev]);
    });
  }, [api, currentFileName, selectedIndices, editedData, handleStatusUpdate]);

  const handleClearSelections = useCallback(() => {
    setSelectedIndices(new Set());
  }, []);

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
            onNextStep={handleNextStep}
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
            starSubmissionResponse={api.starSubmissionResponse}
          />
        )}
      </div>

      {/* Error message (outside white card) */}
      {api.errorMessage !== null && <ErrorMessage message={api.errorMessage} />}
    </div>
  );
}
