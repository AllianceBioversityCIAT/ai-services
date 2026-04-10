'use client';

import { useCallback, useState } from 'react';
import type { BulkUploadResult, RecordStatus, TabType } from '../types';
import { formatCellValueForFilter, getNestedValue } from '../utils/tableHelpers';

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
  const [activeFilters, setActiveFilters] = useState<Record<string, string[]>>({});
  const [currentTab, setCurrentTab] = useState<TabType>('pending');

  // rerender-functional-setstate: use updater form for safe concurrent state
  const setFilter = useCallback((columnKey: string, values: string[]) => {
    setActiveFilters((prev) => ({ ...prev, [columnKey]: values }));
  }, []);

  const clearFilter = useCallback((columnKey: string) => {
    setActiveFilters((prev) => {
      const next = { ...prev };
      delete next[columnKey];
      return next;
    });
  }, []);

  const clearAllFilters = useCallback(() => setActiveFilters({}), []);

  const setTab = useCallback((tab: TabType) => setCurrentTab(tab), []);

  const applyFilters = useCallback(
    (results: BulkUploadResult[], recordStatuses: Record<string, RecordStatus>): BulkUploadResult[] => {
      // First: filter by tab status (rerender-derived-state pattern)
      let filtered = results.filter((result) => {
        const recordId = String(result.id);
        const status = recordStatuses[recordId]?.status ?? 'pending';
        return currentTab === 'pending' ? status === 'pending' || status === 'failed' : status === 'complete';
      });

      // Then: apply column filters (js-early-exit inside filter)
      if (Object.keys(activeFilters).length > 0) {
        filtered = filtered.filter((result) => {
          for (const [columnKey, selectedValues] of Object.entries(activeFilters)) {
            if (selectedValues.length === 0) continue;
            const cellValue = formatCellValueForFilter(getNestedValue(result, columnKey));
            if (!selectedValues.includes(cellValue)) return false;
          }
          return true;
        });
      }

      return filtered;
    },
    [activeFilters, currentTab],
  );

  return { activeFilters, currentTab, setFilter, clearFilter, clearAllFilters, setTab, applyFilters };
}
