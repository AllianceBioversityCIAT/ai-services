import type { DynamoStatuses } from '../types';
import { API_BASE_URL } from '../constants';

/** Loads previously saved record statuses from DynamoDB for a given file. */
export async function loadRecordStatuses(fileName: string): Promise<DynamoStatuses> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/dynamo/bulk-upload-records/${encodeURIComponent(fileName)}`,
      { method: 'GET', headers: { 'Content-Type': 'application/json' } },
    );
    if (!response.ok) {
      if (response.status === 404) return { complete: [], failed: [], links: {} };
      throw new Error(`Failed to load record statuses: ${response.status}`);
    }
    return (await response.json()) as DynamoStatuses;
  } catch (error) {
    console.error('Error loading record statuses:', error);
    return { complete: [], failed: [], links: {} };
  }
}

/** Saves or updates a single record's status in DynamoDB. */
export async function saveRecordStatus(
  fileName: string,
  recordId: string,
  status: 'complete' | 'failed' | 'pending',
  link: string | null = null,
  title?: string,
  contractCode?: string,
  submissionType?: 'approved' | 'draft',
  year?: string,
): Promise<void> {
  const payload = { fileName, recordId, status, link, title, contractCode, submissionType, year };
  const response = await fetch(`${API_BASE_URL}/dynamo/bulk-upload-records`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to save record status: ${response.status} - ${errorText}`);
  }
}
