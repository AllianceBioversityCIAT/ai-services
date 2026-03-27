'use client';

import { useCallback, useState } from 'react';
import type { BulkUploadResult, RecordStatus, StarApiResponse } from '../types';
import { API_BASE_URL, ENVIRONMENT_URL, FOLDER_PATH, S3_BUCKET, STAR_API_URL } from '../constants';
import { extractInnerResults, formatResultForSTAR } from '../utils/dataFormatters';
import { loadRecordStatuses, saveRecordStatus } from './useDynamoDB';
import { simplifyS3Path } from '../utils/tableHelpers';

// =========================
// Auth Token
// =========================
async function fetchAuthToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/auth/token`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Failed to obtain auth token: ${response.status}`);
  const data = (await response.json()) as { token: string };
  return data.token;
}

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
    onSuccess: (results: BulkUploadResult[], recordStatuses: Record<string, RecordStatus>, fileName: string) => void,
  ) => Promise<void>;
  submitToSTAR: (
    selectedResults: BulkUploadResult[],
    currentFileName: string,
    authToken: string,
    onStatusUpdate: (statuses: Record<string, RecordStatus>) => void,
    onRerender: () => void,
  ) => Promise<void>;
  loadS3Objects: (searchTerm?: string) => Promise<void>;
  downloadTemplate: (language: 'es' | 'en') => Promise<void>;
  clearError: () => void;
}

export function useBulkUploadApi(): BulkUploadApiState & BulkUploadApiActions {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Processing...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
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
      onSuccess: (results: BulkUploadResult[], statuses: Record<string, RecordStatus>, fileName: string) => void,
    ) => {
      let token = authToken;
      if (!token) {
        try {
          showLoading('Authenticating...');
          token = await fetchAuthToken();
          setAuthToken(token);
          hideLoading();
        } catch (error) {
          hideLoading();
          showError((error as Error).message);
          return;
        }
      }

      const formData = new FormData();
      formData.append('bucketName', S3_BUCKET);
      formData.append('token', token);
      formData.append('environmentUrl', ENVIRONMENT_URL);

      let fileName: string;
      if (mode === 'upload' && file) {
        const fullKey = FOLDER_PATH + file.name;
        formData.append('file', file);
        formData.append('key', fullKey);
        fileName = file.name;
      } else if (mode === 's3' && s3Key) {
        formData.append('key', s3Key);
        fileName = s3Key.split('/').pop() ?? s3Key;
      } else {
        showError('Invalid document source');
        return;
      }

      try {
        showLoading('Sending document to the service...');
        const response = await fetch(`${API_BASE_URL}/star/mining-bulk-upload/capdev`, {
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

        const payload = extractInnerResults(result);
        const results = payload.results;

        // Load DynamoDB statuses (async-parallel: start early, use result below)
        showLoading('Loading previous statuses...');
        const savedStatuses = await loadRecordStatuses(fileName);
        hideLoading();

        // Build recordStatuses map (js-index-maps)
        const statuses: Record<string, RecordStatus> = {};
        savedStatuses.complete?.forEach((id) => {
          statuses[String(id)] = { status: 'complete', link: savedStatuses.links?.[id] ?? null };
        });
        savedStatuses.failed?.forEach((id) => {
          statuses[String(id)] = { status: 'failed', link: null };
        });
        results.forEach((r) => {
          const rid = String(r.id);
          if (r.id && !statuses[rid]) statuses[rid] = { status: 'pending', link: null };
        });

        onSuccess(results, statuses, fileName);
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
      onStatusUpdate: (statuses: Record<string, RecordStatus>) => void,
      onRerender: () => void,
    ) => {
      try {
        showLoading(`Submitting ${selectedResults.length} records to STAR platform...`);
        const formattedResults = selectedResults.map(formatResultForSTAR);

        const response = await fetch(STAR_API_URL, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ results: formattedResults }),
        });

        hideLoading();

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`STAR API error ${response.status}: ${errorText}`);
        }

        const starResponse = (await response.json()) as StarApiResponse;
        setStarSubmissionResponse(starResponse);

        // Build map for O(1) lookup (js-index-maps)
        const resultsByTitle = new Map(selectedResults.map((r) => [r.title, r]));
        const newStatuses: Record<string, RecordStatus> = {};

        // Process successes and failures in parallel-safe sequential loops
        const saves: Promise<void>[] = [];

        for (const created of starResponse.data?.results_created ?? []) {
          if (!created.error && created.title) {
            const orig = resultsByTitle.get(created.title);
            if (orig?.id) {
              const rid = String(orig.id);
              const starLink = `https://allianceindicatorstest.ciat.cgiar.org/result/STAR-${created.result_official_code}`;
              newStatuses[rid] = { status: 'complete', link: starLink };
              saves.push(saveRecordStatus(currentFileName, rid, 'complete', starLink).catch(console.error));
            }
          }
        }

        for (const err of starResponse.data?.results_errors ?? []) {
          if (err.error && err.title) {
            const orig = resultsByTitle.get(err.title);
            if (orig?.id) {
              const rid = String(orig.id);
              newStatuses[rid] = { status: 'failed', link: null, errorMessage: err.message_error };
              saves.push(saveRecordStatus(currentFileName, rid, 'failed', null).catch(console.error));
            }
          }
        }

        // Fire-and-forget DynamoDB saves (server-after-nonblocking pattern)
        Promise.all(saves).catch(console.error);

        onStatusUpdate(newStatuses);
        onRerender();
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
      const filename = language === 'es' ? 'capdev_guide_spanish.zip' : 'capdev_guide_english.zip';
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
