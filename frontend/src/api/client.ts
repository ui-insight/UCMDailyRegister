import { getSubmitterRoleHeaders } from '../utils/submitterRole';

const BASE_URL = '/api/v1';

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
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getSubmitterRoleHeaders(),
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
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
