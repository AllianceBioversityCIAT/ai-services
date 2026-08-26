'use client';

import { useCallback, useMemo, useState } from 'react';
import type { BulkUploadResult, RecordStatus, TabType, TableSortConfig } from '../types';
import { applyTableSort } from '../utils/tableHelpers';

type SortByTab = Record<TabType, TableSortConfig | null>;

const EMPTY_SORT_BY_TAB: SortByTab = {
  pending: null,
  submitted: null,
};

export interface TableSortState {
  activeSort: TableSortConfig | null;
}

export interface TableSortActions {
  setSort: (config: TableSortConfig) => void;
  clearSort: () => void;
  clearAllSorts: () => void;
  setTab: (tab: TabType) => void;
  applySort: (results: BulkUploadResult[], recordStatuses: Record<string, RecordStatus>) => BulkUploadResult[];
}

export function useTableSort(initialTab: TabType = 'pending'): TableSortState & TableSortActions & { currentTab: TabType } {
  const [sortByTab, setSortByTab] = useState<SortByTab>(EMPTY_SORT_BY_TAB);
  const [currentTab, setCurrentTab] = useState<TabType>(initialTab);

  const activeSort = useMemo(
    () => sortByTab[currentTab] ?? null,
    [sortByTab, currentTab],
  );

  const setSort = useCallback((config: TableSortConfig) => {
    setSortByTab((prev) => ({ ...prev, [currentTab]: config }));
  }, [currentTab]);

  const clearSort = useCallback(() => {
    setSortByTab((prev) => ({ ...prev, [currentTab]: null }));
  }, [currentTab]);

  const clearAllSorts = useCallback(() => setSortByTab(EMPTY_SORT_BY_TAB), []);

  const setTab = useCallback((tab: TabType) => setCurrentTab(tab), []);

  const applySort = useCallback(
    (results: BulkUploadResult[], recordStatuses: Record<string, RecordStatus>): BulkUploadResult[] =>
      applyTableSort(results, sortByTab[currentTab] ?? null, recordStatuses, currentTab),
    [sortByTab, currentTab],
  );

  return { activeSort, currentTab, setSort, clearSort, clearAllSorts, setTab, applySort };
}
