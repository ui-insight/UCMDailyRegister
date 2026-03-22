import { getSubmitterRoleHeaders } from '../utils/submitterRole';

const BASE_URL = '/api/v1';

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
    throw new Error(error.detail || res.statusText);
  }
  if (res.status === 204 || res.status === 205) {
    return undefined as T;
  }

  if (res.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return res.json();
}
