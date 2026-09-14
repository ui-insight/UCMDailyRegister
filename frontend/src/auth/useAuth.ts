import { useEffect, useState, useSyncExternalStore } from 'react';
import { getAuthConfig } from '../api/auth';
import { getIdentity, subscribe, type Identity } from './tokenStore';

const NO_IDENTITY = () => null;

/** The signed-in identity, re-rendering when the token store changes. */
export function useIdentity(): Identity | null {
  return useSyncExternalStore(subscribe, getIdentity, NO_IDENTITY);
}

let cachedSsoEnabled: boolean | null = null;

/**
 * Whether this deployment signs users in through Entra rather than the
 * trusted proxy header. `null` until the backend answers, so callers can
 * avoid flashing the wrong screen. Cached for the page's lifetime: it is a
 * deployment property, not something that changes between renders.
 */
export function useSsoEnabled(): boolean | null {
  const [enabled, setEnabled] = useState<boolean | null>(cachedSsoEnabled);

  useEffect(() => {
    if (cachedSsoEnabled !== null) return undefined;
    let cancelled = false;
    getAuthConfig()
      .then((config) => {
        cachedSsoEnabled = config.sso_enabled;
        if (!cancelled) setEnabled(config.sso_enabled);
      })
      .catch(() => {
        // Never strand the user on a check: fall back to today's behavior.
        if (!cancelled) setEnabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return enabled;
}

/** Test hook: forget the cached deployment answer. */
export function resetSsoEnabledCache() {
  cachedSsoEnabled = null;
}
