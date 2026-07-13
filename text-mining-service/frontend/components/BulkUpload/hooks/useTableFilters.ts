'use client';

import { useCallback, useMemo, useState } from 'react';
import type { BulkUploadResult, RecordStatus, TabType } from '../types';
import { getColumnFilterTokens } from '../utils/tableHelpers';

type FiltersByTab = Record<TabType, Record<string, string[]>>;

const EMPTY_FILTERS_BY_TAB: FiltersByTab = {
  pending: {},
  submitted: {},
};

export interface TableFiltersState {
  activeFilters: Record<string, string[]>;
  currentTab: TabType;
}

export interface TableFiltersActions {
  setFilter: (columnKey: string, values: string[]) => void;
  clearFilter: (columnKey: string) => void;
  clearAllFilters: () => void;
  setTab: (tab: TabType) => void;
  applyFilters: (results: BulkUploadResult[], recordStatuses: Record<string, RecordStatus>) => BulkUploadResult[];
}

export function useTableFilters(): TableFiltersState & TableFiltersActions {
  const [filtersByTab, setFiltersByTab] = useState<FiltersByTab>(EMPTY_FILTERS_BY_TAB);
  const [currentTab, setCurrentTab] = useState<TabType>('pending');

  // Filters are scoped to the active tab so Pending and Submitted never conflict
  const activeFilters = useMemo(
    () => filtersByTab[currentTab] ?? {},
    [filtersByTab, currentTab],
  );

  const setFilter = useCallback((columnKey: string, values: string[]) => {
    setFiltersByTab((prev) => ({
      ...prev,
      [currentTab]: { ...prev[currentTab], [columnKey]: values },
    }));
  }, [currentTab]);

  const clearFilter = useCallback((columnKey: string) => {
    setFiltersByTab((prev) => {
      const nextForTab = { ...prev[currentTab] };
      delete nextForTab[columnKey];
      return { ...prev, [currentTab]: nextForTab };
    });
  }, [currentTab]);

  const clearAllFilters = useCallback(
    () => setFiltersByTab({ pending: {}, submitted: {} }),
    [],
  );

  const setTab = useCallback((tab: TabType) => setCurrentTab(tab), []);

  const applyFilters = useCallback(
    (results: BulkUploadResult[], recordStatuses: Record<string, RecordStatus>): BulkUploadResult[] => {
      // First: filter by tab status (rerender-derived-state pattern)
      let filtered = results.filter((result) => {
        const recordId = String(result.id);
        const status = recordStatuses[recordId]?.status ?? 'pending';
        return currentTab === 'pending' ? status === 'pending' || status === 'failed' : status === 'complete';
      });

      // Deduplicate by id so reinjected + remined rows never inflate Submitted Results
      const uniqueById = new Map<string, BulkUploadResult>();
      for (const result of filtered) {
        if (result.id == null) continue;
        uniqueById.set(String(result.id), result);
      }
      filtered = Array.from(uniqueById.values());

      // Then: apply column filters for the active tab only
      const tabFilters = filtersByTab[currentTab] ?? {};
      if (Object.keys(tabFilters).length > 0) {
        filtered = filtered.filter((result) => {
          for (const [columnKey, selectedValues] of Object.entries(tabFilters)) {
            if (selectedValues.length === 0) continue;
            const recordStatus = recordStatuses[String(result.id)];
            const tokens = getColumnFilterTokens(columnKey, result, recordStatus, currentTab);
            const hasMatch = tokens.some(t => selectedValues.includes(t));
            if (!hasMatch) return false;
          }
          return true;
        });
      }

      return filtered;
    },
    [filtersByTab, currentTab],
  );

  return { activeFilters, currentTab, setFilter, clearFilter, clearAllFilters, setTab, applyFilters };
}
