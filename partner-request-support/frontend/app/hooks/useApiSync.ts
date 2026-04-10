'use client';

import { useState } from 'react';
import { partnerService } from '../services/partnerService';
import { ApiPartnerRequest } from '../types/api.types';

export const useApiSync = () => {
  const [apiPartners, setApiPartners] = useState<ApiPartnerRequest[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  const syncPartnerRequests = async () => {
    setSyncing(true);
    setSyncError(null);

    try {
      const partners = await partnerService.syncPartnerRequests();
      setApiPartners(partners);
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
    syncing,
    syncError,
    syncPartnerRequests,
  };
};
