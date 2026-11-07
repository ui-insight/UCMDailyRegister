import { clearToken, getToken } from '../auth/tokenStore';
import { getSubmitterRoleHeaders } from '../utils/submitterRole';

const BASE_URL = '/api/v1';

/** Bearer header for the SSO session token, when one is held. Under the
 * trusted-header deployment there is no token and this is empty. */
function getAuthHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** An API failure that keeps its HTTP status and structured detail. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(formatApiError(detail));
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function formatApiError(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail;
  }

  if (
    detail && typeof detail === 'object' && !Array.isArray(detail)
    && 'message' in detail && typeof detail.message === 'string'
  ) {
    return detail.message;
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

/**
 * Send an API request with the caller's credentials (SSO bearer token or
 * trusted-role headers) and turn an error response into an ApiError.
 */
async function sendRequest(
  path: string,
  options: RequestInit | undefined,
  contentHeaders: HeadersInit,
): Promise<Response> {
  // Caller headers may add to or override the content type, but never drop
  // the credentials: a later spread of `options` would replace them all.
  const headers = new Headers(contentHeaders);
  new Headers(options?.headers).forEach((value, key) => headers.set(key, value));
  new Headers(getSubmitterRoleHeaders()).forEach((value, key) => headers.set(key, value));
  new Headers(getAuthHeaders()).forEach((value, key) => headers.set(key, value));
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
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
    throw new ApiError(res.status, error.detail ?? error);
  }
  return res;
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await sendRequest(path, options, { 'Content-Type': 'application/json' });
  if (res.status === 204 || res.status === 205) {
    return undefined as T;
  }

  if (res.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return res.json();
}

/** A file returned by the API, with the name the server suggested. */
export interface DownloadedFile {
  blob: Blob;
  filename: string | null;
}

/**
 * Fetch a file with the caller's credentials. A plain link can't carry the
 * SSO bearer token, so downloads of protected files go through here (#476).
 */
/**
 * Send form data (for example a file upload) with the caller's credentials.
 * No Content-Type is set, so the browser adds the multipart boundary.
 */
export async function apiUpload<T>(path: string, body: FormData): Promise<T> {
  const res = await sendRequest(path, { method: 'POST', body }, {});
  return res.json();
}

export async function apiDownload(path: string): Promise<DownloadedFile> {
  const res = await sendRequest(path, undefined, {});
  return {
    blob: await res.blob(),
    filename: filenameFromDisposition(res.headers.get('content-disposition')),
  };
}

export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim());
    } catch {
      // Fall through to the plain filename.
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1].trim() : null;
}

/** Hand a downloaded file to the browser to save. */
export function saveDownloadedFile(file: DownloadedFile, fallbackName: string): void {
  const url = URL.createObjectURL(file.blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = file.filename ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
