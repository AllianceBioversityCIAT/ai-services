import axios from 'axios';
import { ProcessingResults, ApiPartnerRequest } from '../types/api.types';
import { Partner, WebSearch } from '../types/partner.types';

const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const partnerService = {
  async processExcelFile(
    file: File,
    userEmail: string,
    userName: string,
    authToken: string
  ): Promise<ProcessingResults> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_email', userEmail);
    formData.append('user_name', userName);
    formData.append('auth_token', authToken);
    formData.append('create_requests', 'true');

    const response = await axios.post<ProcessingResults>(
      `${getApiUrl()}/api/process-partners`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  async processApiPartners(): Promise<ProcessingResults> {
    const response = await axios.post<ProcessingResults>(
      `${getApiUrl()}/api/process-api-partners`,
      null,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return response.data;
  },

  async downloadTemplate(): Promise<Blob> {
    const response = await axios.get(`${getApiUrl()}/api/download-template`, {
      responseType: 'blob',
    });

    return new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
  },

  async syncPartnerRequests(): Promise<ApiPartnerRequest[]> {
    const response = await axios.get(`${getApiUrl()}/api/sync-partner-requests`);
    return response.data.pending_requests || [];
  },

  async respondToRequest(
    requestId: number,
    userId: number,
    accept: boolean,
    authToken: string,
    rejectJustification?: string
  ): Promise<any> {
    const response = await axios.post(
      `${getApiUrl()}/api/respond-partner-request`,
      {
        request_id: requestId,
        user_id: userId,
        accept,
        reject_justification: rejectJustification?.trim() || 'No justification provided',
        auth_token: authToken,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return response.data;
  },

  async manualWebSearch(
    partnerName: string,
    country: string | null,
    website: string | null
  ): Promise<WebSearch> {
    const response = await axios.post(
      `${getApiUrl()}/api/manual-web-search`,
      {
        partner_name: partnerName,
        country,
        website,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return response.data;
  },

  async clearCache(): Promise<{ success: boolean; cleared: number; message: string }> {
    const response = await axios.post(`${getApiUrl()}/api/clear-cache`);
    return response.data;
  },
};
