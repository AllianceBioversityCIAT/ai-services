'use client';

import { useCallback, useState } from 'react';

export interface PaginationState {
  currentPage: number;
  perPage: number;
  totalItems: number;
}

export interface PaginationActions {
  goToPage: (page: number) => void;
  goFirst: () => void;
  goLast: () => void;
  goNext: () => void;
  goPrev: () => void;
  setPerPage: (perPage: number) => void;
  reset: () => void;
}

export interface PaginationDerived {
  totalPages: number;
  startIndex: number;
  endIndex: number;
  setTotalItems: (n: number) => void;
}

export function usePagination(initialPerPage: number): PaginationState & PaginationActions & PaginationDerived {
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPageState] = useState(initialPerPage);
  const [totalItems, setTotalItems] = useState(0);

  // Derived values computed during render (rerender-derived-state-no-effect)
  const totalPages = Math.max(1, Math.ceil(totalItems / perPage));
  const startIndex = (currentPage - 1) * perPage;
  const endIndex = Math.min(startIndex + perPage, totalItems);

  const goToPage = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const goFirst = useCallback(() => setCurrentPage(1), []);

  const goLast = useCallback(
    () => setCurrentPage((prev) => Math.max(1, Math.ceil(totalItems / perPage))),
    [totalItems, perPage],
  );

  const goNext = useCallback(
    () => setCurrentPage((prev) => {
      const max = Math.max(1, Math.ceil(totalItems / perPage));
      return Math.min(prev + 1, max);
    }),
    [totalItems, perPage],
  );

  const goPrev = useCallback(() => setCurrentPage((prev) => Math.max(prev - 1, 1)), []);

  const setPerPage = useCallback((newPerPage: number) => {
    setPerPageState(newPerPage);
    setCurrentPage(1);
  }, []);

  const reset = useCallback(() => {
    setCurrentPage(1);
  }, []);

  return {
    currentPage,
    perPage,
    totalItems,
    totalPages,
    startIndex,
    endIndex,
    setTotalItems,
    goToPage,
    goFirst,
    goLast,
    goNext,
    goPrev,
    setPerPage,
    reset,
  };
}
