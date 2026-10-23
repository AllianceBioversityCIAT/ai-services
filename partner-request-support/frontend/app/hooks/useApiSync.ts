'use client';

import { useState } from 'react';
import { partnerService } from '../services/partnerService';
import { ApiPartnerRequest } from '../types/api.types';

export const useApiSync = () => {
  const [apiPartners, setApiPartners] = useState<ApiPartnerRequest[]>([]);
  // How many of them the backend processes per run; it decides, we only display it.
  const [batchSize, setBatchSize] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const syncPartnerRequests = async () => {
    setSyncing(true);
    setSyncError(null);

    try {
      const data = await partnerService.syncPartnerRequests();
      const partners = data.pending_requests || [];
      setApiPartners(partners);
      setBatchSize(data.batch_size ?? 0);
      return partners;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error syncing partner requests';
      setSyncError(errorMsg);
      console.error('Sync error:', err);
      throw err;
    } finally {
      setSyncing(false);
    }
  };

  return {
    apiPartners,
    batchSize,
    syncing,
    syncError,
    syncPartnerRequests,
  };
};
