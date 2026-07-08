'use client';

import { useEffect, useRef } from 'react';

const LEAVE_MESSAGE =
  'You have work in progress. Are you sure you want to leave? You may need to process the document again.';

/**
 * Prompts before the user leaves via browser back/forward, refresh, or tab close.
 * Also pairs with overscroll-behavior CSS to reduce accidental trackpad back navigation.
 */
export function useNavigationGuard(enabled: boolean): void {
  const guardActiveRef = useRef(false);

  useEffect(() => {
    if (!enabled) {
      guardActiveRef.current = false;
      return;
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };

    const handlePopState = () => {
      const shouldLeave = window.confirm(LEAVE_MESSAGE);
      if (shouldLeave) {
        guardActiveRef.current = false;
        window.history.back();
        return;
      }
      window.history.pushState({ navigationGuard: true }, '', window.location.href);
      guardActiveRef.current = true;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('popstate', handlePopState);

    if (!guardActiveRef.current) {
      window.history.pushState({ navigationGuard: true }, '', window.location.href);
      guardActiveRef.current = true;
    }

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('popstate', handlePopState);
    };
  }, [enabled]);
}
