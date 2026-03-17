'use client';

import { useState } from 'react';
import { partnerService } from '../services/partnerService';
import { Partner, WebSearch } from '../types/partner.types';
import { ProcessingResults } from '../types/api.types';

export const useWebSearch = (results: ProcessingResults | null, setResults: (results: ProcessingResults) => void) => {
  const [runningWebSearch, setRunningWebSearch] = useState<{ [partnerId: string]: boolean }>({});

  const runManualWebSearch = async (partner: Partner) => {
    const partnerId = partner.id;
    setRunningWebSearch((prev) => ({ ...prev, [partnerId]: true }));

    try {
      const webSearchData = await partnerService.manualWebSearch(
        partner.name,
        partner.country || null,
        partner.website || null
      );

      if (results) {
        const updatedPartners = results.partners.map((p) =>
          p.id === partnerId ? { ...p, web_search: webSearchData } : p
        );

        setResults({
          ...results,
          partners: updatedPartners,
          stats: {
            ...results.stats,
            web_search_attempted: results.stats.web_search_attempted + 1,
            web_search_success: webSearchData.success
              ? results.stats.web_search_success + 1
              : results.stats.web_search_success,
          },
        });

        return { ...partner, web_search: webSearchData };
      }

      return null;
    } catch (err: any) {
      console.error('Error running manual web search:', err);
      throw err;
    } finally {
      setRunningWebSearch((prev) => ({ ...prev, [partnerId]: false }));
    }
  };

  return {
    runningWebSearch,
    runManualWebSearch,
  };
};
