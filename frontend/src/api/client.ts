import { clearToken, getToken } from '../auth/tokenStore';
import { getSubmitterRoleHeaders } from '../utils/submitterRole';

const BASE_URL = '/api/v1';

/** Bearer header for the SSO session token, when one is held. Under the
 * trusted-header deployment there is no token and this is empty. */
function getAuthHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function formatApiError(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (item && typeof item === 'object') {
        const maybeMessage = 'msg' in item ? item.msg : undefined;
        const maybeLocation = 'loc' in item ? item.loc : undefined;

        if (typeof maybeMessage === 'string') {
          const location = Array.isArray(maybeLocation)
            ? maybeLocation
              .filter((part) => part !== 'body')
              .map(String)
              .join(' > ')
            : '';
          return location ? `${location}: ${maybeMessage}` : maybeMessage;
        }
      }

      return JSON.stringify(item);
    }).filter(Boolean);

    if (messages.length > 0) {
      return messages.join('; ');
    }
  }

  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail);
  }

  return 'Request failed';
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...getSubmitterRoleHeaders(),
        ...getAuthHeaders(),
        ...options?.headers,
      },
      ...options,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new Error(
      'Unable to reach the UCM service. Check your connection and retry. '
      + 'If the problem continues, report it to the application maintainers.',
      { cause: error },
    );
  }
  if (!res.ok) {
    if (res.status === 401 && getToken()) {
      // The backend refused our session token (expired, or SECRET_KEY was
      // rotated). Drop it so the app falls back to signed-out and the
      // landing page offers sign-in again, rather than 401-ing forever.
      clearToken();
    }
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(formatApiError(error.detail ?? error));
  }
  if (res.status === 204 || res.status === 205) {
    return undefined as T;
  }

  if (res.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return res.json();
}
