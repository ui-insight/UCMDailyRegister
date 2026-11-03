import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { getAuthConfig } from '../api/auth';
import { getIdentity, subscribe, type Identity } from './tokenStore';

const NO_IDENTITY = () => null;

/** The signed-in identity, re-rendering when the token store changes. */
export function useIdentity(): Identity | null {
  return useSyncExternalStore(subscribe, getIdentity, NO_IDENTITY);
}

/**
 * How this deployment authenticates: `sso` (Entra sign-in), `header` (the
 * trusted proxy header, used for local development), `error` when the
 * backend could not be asked, or `null` while the answer is pending.
 */
export type AuthMode = 'sso' | 'header' | 'error' | null;

// Only a real answer is cached: it is a deployment property, not something
// that changes between renders. A failure is retried on request.
let cachedMode: 'sso' | 'header' | null = null;

/** The deployment's auth mode, plus a way to ask again after a failure. */
export function useAuthMode(): { mode: AuthMode; retry: () => void } {
  const [mode, setMode] = useState<AuthMode>(cachedMode);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (cachedMode !== null) return undefined;
    let cancelled = false;
    getAuthConfig()
      .then((config) => {
        cachedMode = config.sso_enabled ? 'sso' : 'header';
        if (!cancelled) setMode(cachedMode);
      })
      .catch(() => {
        if (!cancelled) setMode('error');
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setMode(null);
    setAttempt((value) => value + 1);
  }, []);

  return { mode, retry };
}

/**
 * Whether this deployment signs users in through Entra rather than the
 * trusted proxy header. `null` until the backend answers, so callers can
 * avoid flashing the wrong screen. If the backend cannot be asked this
 * reports `false`, so the route guard never strands anyone on a check; the
 * landing page uses `useAuthMode` instead, because it must not offer
 * anonymous submission to an SSO deployment it failed to reach.
 */
export function useSsoEnabled(): boolean | null {
  const { mode } = useAuthMode();
  if (mode === null) return null;
  return mode === 'sso';
}

/** Test hook: forget the cached deployment answer. */
export function resetSsoEnabledCache() {
  cachedMode = null;
}
