export const LOGIN_PATH = '/login';

/** Build the login URL for a destination, so callers never assemble it by hand. */
export function loginUrlFor(next?: string | null): string {
  const params = new URLSearchParams();
  if (next && next !== '/') params.set('next', next);
  const query = params.toString();
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH;
}
