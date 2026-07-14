'use client';

import { useCallback, useState } from 'react';
import type { BulkUploadResult, RecordStatus, StarApiResponse } from '../types';
import { API_BASE_URL, ENVIRONMENT_URL, FOLDER_PATH, S3_BUCKET, STAR_API_URL } from '../constants';
import { extractInnerResults, formatResultForSTAR } from '../utils/dataFormatters';
import { loadRecordStatuses, saveRecordStatusesBatch } from './useDynamoDB';
import type { RecordStatusSavePayload } from './useDynamoDB';
import { simplifyS3Path } from '../utils/tableHelpers';
import { checkCompleteness } from '../utils/completenessChecker';

// =========================
// Hook
// =========================
export interface BulkUploadApiState {
  isLoading: boolean;
  loadingText: string;
  errorMessage: string | null;
  authToken: string | null;
  s3Objects: string[];
  starSubmissionResponse: StarApiResponse | null;
}

export interface BulkUploadApiActions {
  processDocument: (
    mode: 'upload' | 's3',
    file: File | null,
    s3Key: string | null,
    onSuccess: (results: BulkUploadResult[], recordStatuses: Record<string, RecordStatus>, fileName: string, interactionId: string | null) => void,
  ) => Promise<void>;
  submitToSTAR: (
    selectedResults: BulkUploadResult[],
    currentFileName: string,
    authToken: string,
    onComplete: (completeIds: Set<string>, newStatuses: Record<string, RecordStatus>) => void,
    interactionId?: string | null,
    editedIds?: Set<string>,
  ) => Promise<void>;
  loadS3Objects: (searchTerm?: string) => Promise<void>;
  downloadTemplate: (language: 'es' | 'en') => Promise<void>;
  clearError: () => void;
}

export function useBulkUploadApi(initialToken: string | null = null, userId: string | null = null, userName: string | null = null): BulkUploadApiState & BulkUploadApiActions {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Processing...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const authToken: string | null = initialToken;
  const [s3Objects, setS3Objects] = useState<string[]>([]);
  const [starSubmissionResponse, setStarSubmissionResponse] = useState<StarApiResponse | null>(null);

  const showLoading = useCallback((text = 'Processing...') => {
    setLoadingText(text);
    setIsLoading(true);
  }, []);

  const hideLoading = useCallback(() => setIsLoading(false), []);

  const showError = useCallback((message: string) => {
    setErrorMessage(message);
    setTimeout(() => setErrorMessage(null), 8000);
  }, []);

  const clearError = useCallback(() => setErrorMessage(null), []);

  // ---- Process Document ----
  const processDocument = useCallback(
    async (
      mode: 'upload' | 's3',
      file: File | null,
      s3Key: string | null,
      onSuccess: (results: BulkUploadResult[], statuses: Record<string, RecordStatus>, fileName: string, interactionId: string | null) => void,
    ) => {
      const token = authToken;
      if (!token) {
        showError('No authentication token available. Please reload the page.');
        return;
      }

      let fileName: string;
      if (mode === 'upload' && file) {
        fileName = file.name;
      } else if (mode === 's3' && s3Key) {
        fileName = s3Key.split('/').pop() ?? s3Key;
      } else {
        showError('Invalid document source');
        return;
      }

      try {
        // Load DynamoDB statuses BEFORE mining so we can skip already-submitted rows
        showLoading('Loading previous statuses...');
        const savedStatuses = await loadRecordStatuses(fileName);

        // Build skip list from already-complete records
        const completeIdSet = new Set(savedStatuses.complete?.map(String) ?? []);
        const skipIds = Array.from(completeIdSet);

        const formData = new FormData();
        formData.append('bucketName', S3_BUCKET);
        formData.append('token', token);
        formData.append('environmentUrl', ENVIRONMENT_URL);
        if (skipIds.length > 0) {
          formData.append('skip_ids', skipIds.join(','));
        }
        if (userId) {
          formData.append('user_id', userId);
        }
        if (userName) {
          formData.append('user_name', userName);
        }

        if (mode === 'upload' && file) {
          const fullKey = FOLDER_PATH + file.name;
          formData.append('file', file);
          formData.append('key', fullKey);
        } else if (mode === 's3' && s3Key) {
          formData.append('key', s3Key);
        }

        showLoading('Sending document to the service...');
        const response = await fetch('/api/bulk-upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`API error ${response.status}: ${errorText}`);
        }

        const result = (await response.json()) as Record<string, unknown>;
        hideLoading();

        if (result.status === 'error' || result.isError === true) {
          showError(`Service returned an error: ${String(result.error ?? result.message ?? 'Unknown error')}`);
          return;
        }

        // interaction_id may be at top level of the HTTP response, or embedded
        // inside the MCP content text alongside `results`.
        let interactionId: string | null = typeof result.interaction_id === 'string' ? result.interaction_id : null;
        if (!interactionId && Array.isArray(result.content)) {
          for (const item of result.content as Array<{ text?: string }>) {
            if (item.text) {
              try {
                const parsed = JSON.parse(item.text) as Record<string, unknown>;
                if (typeof parsed.interaction_id === 'string') {
                  interactionId = parsed.interaction_id;
                  break;
                }
              } catch { /* ignore */ }
            }
          }
        }
        const payload = extractInnerResults(result);
        const aiResults = payload.results.map((r) => ({
          ...r,
          is_partner_not_applicable: !Array.isArray(r.partners) || r.partners.length === 0,
        }));

        // Re-inject already-submitted records using stored DynamoDB data so they appear in the table.
        // Skip IDs already returned by AI to avoid duplicate rows in Submitted Results.
        const aiIdSet = new Set(aiResults.map((r) => String(r.id)));
        const injectedResults: BulkUploadResult[] = [];
        for (const id of skipIds) {
          if (aiIdSet.has(id)) continue;
          const stored = savedStatuses.record_data?.[id];
          injectedResults.push({
            id,
            title: stored?.title ?? `Record ${id}`,
            contract_code: stored?.contract_code ?? undefined,
            year: stored?.year ?? undefined,
          } as BulkUploadResult);
        }

        // Deduplicate by id (last occurrence wins) in case of any residual overlap
        const mergedById = new Map<string, BulkUploadResult>();
        for (const r of [...injectedResults, ...aiResults]) {
          if (r.id == null) continue;
          mergedById.set(String(r.id), { ...r, id: String(r.id) });
        }
        const results = Array.from(mergedById.values());

        // Build recordStatuses map — Dynamo is the source of truth for submitted records
        const statuses: Record<string, RecordStatus> = {};
        savedStatuses.complete?.forEach((id) => {
          const rid = String(id);
          const stored = savedStatuses.record_data?.[rid] ?? savedStatuses.record_data?.[id];
          statuses[rid] = {
            status: 'complete',
            link: savedStatuses.links?.[rid] ?? savedStatuses.links?.[id] ?? null,
            submissionType: (stored?.submission_type as 'approved' | 'draft' | undefined) ?? undefined,
          };
        });
        savedStatuses.failed?.forEach((id) => {
          statuses[String(id)] = { status: 'failed', link: null };
        });
        results.forEach((r) => {
          const rid = String(r.id);
          if (r.id && !statuses[rid]) statuses[rid] = { status: 'pending', link: null };
        });

        onSuccess(results, statuses, fileName, interactionId);
      } catch (error) {
        hideLoading();
        showError(`Could not reach the API: ${(error as Error).message}`);
      }
    },
    [authToken, showLoading, hideLoading, showError],
  );

  // ---- Submit to STAR ----
  const submitToSTAR = useCallback(
    async (
      selectedResults: BulkUploadResult[],
      currentFileName: string,
      token: string,
      onComplete: (completeIds: Set<string>, newStatuses: Record<string, RecordStatus>) => void,
      interactionId?: string | null,
      editedIds?: Set<string>,
    ) => {
      try {
        // Compute completeness once per result to avoid double-checking
        const completenessMap = new Map(
          selectedResults.map((r) => [String(r.id), checkCompleteness(r)]),
        );
        const completeResults = selectedResults.filter((r) => completenessMap.get(String(r.id))!.isComplete);

        // Process-level metadata — sent alongside every STAR request
        const processMeta = {
          file_name: currentFileName,
          ai_interaction_id: interactionId ?? null,
        };

        // Helper: attach result-level metadata to each formatted result
        const withMeta = (r: BulkUploadResult, status: number) => ({
          ...formatResultForSTAR(r),
          status,
          metadata: {
            missing_fields: completenessMap.get(String(r.id))?.missing_fields ?? [],
            manually_edited: editedIds?.has(String(r.id)) ?? false,
          },
        });

        showLoading(`Submitting ${selectedResults.length} record${selectedResults.length !== 1 ? 's' : ''} to STAR...`);

        // Single bulk request: status 4 (draft) or 6 (approved) per result
        const payload = {
          results: selectedResults.map((r) =>
            withMeta(r, completenessMap.get(String(r.id))!.isComplete ? 6 : 4),
          ),
          metadata: processMeta,
        };
        console.log('[BulkUpload] STAR payload:', JSON.parse(JSON.stringify(payload)));

        const response = await fetch(STAR_API_URL, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`STAR API error ${response.status}: ${errorText}`);
        }

        const starResponse = (await response.json()) as StarApiResponse;
        setStarSubmissionResponse(starResponse);

        // Build map for O(1) lookup (js-index-maps)
        const resultsByTitle = new Map(selectedResults.map((r) => [r.title, r]));
        const completeIdSet = new Set(completeResults.map((r) => String(r.id)));
        const newStatuses: Record<string, RecordStatus> = {};
        const dynamoUpdates: RecordStatusSavePayload[] = [];

        for (const created of starResponse.data?.results_created ?? []) {
          if (!created.error && created.title) {
            const orig = resultsByTitle.get(created.title);
            if (orig?.id) {
              const rid = String(orig.id);
              const starLink = `https://star.alliance.cgiar.org/result/STAR-${created.result_official_code}`;
              const submissionType = completeIdSet.has(rid) ? 'approved' : 'draft';
              newStatuses[rid] = { status: 'complete', link: starLink, submissionType };
              dynamoUpdates.push({
                recordId: rid,
                status: 'complete',
                link: starLink,
                title: orig.title,
                contractCode: orig.contract_code ?? undefined,
                submissionType,
                year: orig.year != null ? String(orig.year) : undefined,
              });
            }
          }
        }

        for (const err of starResponse.data?.results_errors ?? []) {
          if (err.error && err.title) {
            const orig = resultsByTitle.get(err.title);
            if (orig?.id) {
              const rid = String(orig.id);
              newStatuses[rid] = { status: 'failed', link: null, errorMessage: err.message_error };
              dynamoUpdates.push({
                recordId: rid,
                status: 'failed',
                link: null,
                title: orig.title,
                contractCode: orig.contract_code ?? undefined,
                year: orig.year != null ? String(orig.year) : undefined,
              });
            }
          }
        }

        // Persist all statuses in one atomic DynamoDB write before updating the UI
        if (dynamoUpdates.length > 0) {
          showLoading('Saving submission statuses...');
          try {
            const saved = await saveRecordStatusesBatch(currentFileName, dynamoUpdates);
            const updatedIds = new Set(dynamoUpdates.map((u) => u.recordId));
            const savedComplete = new Set((saved.complete ?? []).map(String));
            const savedFailed = new Set((saved.failed ?? []).map(String));
            // Align only this submission's statuses with what Dynamo persisted
            for (const rid of updatedIds) {
              if (savedComplete.has(rid)) {
                const stored = saved.record_data?.[rid];
                newStatuses[rid] = {
                  status: 'complete',
                  link: saved.links?.[rid] ?? newStatuses[rid]?.link ?? null,
                  submissionType:
                    (stored?.submission_type as 'approved' | 'draft' | undefined) ??
                    newStatuses[rid]?.submissionType,
                };
              } else if (savedFailed.has(rid)) {
                newStatuses[rid] = {
                  status: 'failed',
                  link: null,
                  errorMessage: newStatuses[rid]?.errorMessage,
                };
              }
            }
          } catch (saveError) {
            console.error('Failed to persist statuses to DynamoDB:', saveError);
            showError(
              `Records were submitted to STAR, but saving statuses failed: ${(saveError as Error).message}. Re-check Submitted Results after refresh.`,
            );
          }
        }

        hideLoading();
        onComplete(new Set(completeResults.map((r) => String(r.id))), newStatuses);
      } catch (error) {
        hideLoading();
        showError(`Error submitting to STAR: ${(error as Error).message}`);
      }
    },
    [showLoading, hideLoading, showError],
  );

  // ---- Load S3 Objects ----
  const loadS3Objects = useCallback(
    async (searchTerm = '') => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/s3/list?bucket=${S3_BUCKET}&prefix=${encodeURIComponent(FOLDER_PATH)}`,
        );
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = (await response.json()) as { objects?: string[] };
        let allFiles = data.objects ?? [];

        if (searchTerm) {
          const lowerSearch = searchTerm.toLowerCase();
          allFiles = allFiles.filter((f) => simplifyS3Path(f).toLowerCase().includes(lowerSearch));
        }

        setS3Objects(allFiles);
      } catch (error) {
        showError(`Error loading files: ${(error as Error).message}`);
        setS3Objects([]);
      }
    },
    [showError],
  );

  // ---- Download Template ----
  const downloadTemplate = useCallback(
    async (language: 'es' | 'en') => {
      const label = language === 'es' ? 'Spanish' : 'English';
      const today = new Date();
      const dateSuffix = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
      const langLabel = language === 'es' ? 'spanish' : 'english';
      const filename = `capdev_guide_${langLabel}_${dateSuffix}.zip`;
      try {
        showLoading(`Downloading guide in ${label}...`);
        const response = await fetch(`${API_BASE_URL}/s3/download-template?language=${language}`);
        if (!response.ok) throw new Error(`Failed to download template: ${response.status}`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        hideLoading();
      } catch (error) {
        hideLoading();
        showError(`Error downloading guide: ${(error as Error).message}`);
      }
    },
    [showLoading, hideLoading, showError],
  );

  return {
    isLoading,
    loadingText,
    errorMessage,
    authToken,
    s3Objects,
    starSubmissionResponse,
    processDocument,
    submitToSTAR,
    loadS3Objects,
    downloadTemplate,
    clearError,
  };
}
