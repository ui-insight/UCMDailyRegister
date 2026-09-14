import type { SubmitterRole } from '../utils/submitterRole';

/**
 * The session token minted by the backend after Entra sign-in, plus the
 * identity it carries. Module-level so `apiFetch` can read it without going
 * through React, and hydrated from localStorage at import so the very first
 * request after a page reload already carries the token.
 *
 * The identity is decoded client-side for *display only*. The backend
 * re-verifies the signature on every request; nothing here is trusted for
 * authorization.
 */

const STORAGE_KEY = 'ucm_session_token';

export type SignedInRole = Exclude<SubmitterRole, 'public'>;

export interface Identity {
  subject: string;
  name: string;
  role: SignedInRole;
  /** Expiry, seconds since the epoch. */
  exp: number;
}

type Listener = () => void;

let token: string | null = null;
let identity: Identity | null = null;
const listeners = new Set<Listener>();

function decodeIdentity(raw: string): Identity | null {
  try {
    const [, payload] = raw.split('.');
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    const claims = JSON.parse(json) as Partial<Record<string, unknown>>;
    const role = claims.role;
    if (
      typeof claims.sub !== 'string'
      || typeof claims.name !== 'string'
      || typeof claims.exp !== 'number'
      || (role !== 'staff' && role !== 'slc' && role !== 'ops')
    ) {
      return null;
    }
    if (claims.exp * 1000 <= Date.now()) return null;
    return { subject: claims.sub, name: claims.name, role, exp: claims.exp };
  } catch {
    return null;
  }
}

function readStorage(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStorage(value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // Private mode or blocked storage: the session simply won't survive a reload.
  }
}

function apply(next: string | null) {
  const decoded = next ? decodeIdentity(next) : null;
  // An expired or malformed token is dropped rather than kept around to 401.
  token = decoded ? next : null;
  identity = decoded;
  writeStorage(token);
  listeners.forEach((listener) => listener());
}

if (typeof window !== 'undefined') {
  const stored = readStorage();
  const decoded = stored ? decodeIdentity(stored) : null;
  token = decoded ? stored : null;
  identity = decoded;
  if (stored && !decoded) writeStorage(null);
}

export function getToken(): string | null {
  return token;
}

export function getIdentity(): Identity | null {
  return identity;
}

export function setToken(next: string | null) {
  apply(next);
}

export function clearToken() {
  apply(null);
}

/** Subscribe to token changes; returns an unsubscribe function. */
export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
