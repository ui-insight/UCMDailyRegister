import { apiFetch } from './client';
import type { AuthConfig, CurrentUser } from '../types/auth';

/** Full-page navigations, so they cannot go through `apiFetch`: the whole
 * point is to hand the browser to Microsoft and back. */
export const SSO_LOGIN_URL = '/api/v1/auth/sso/login';
export const SSO_LOGOUT_URL = '/api/v1/auth/logout';

export async function getAuthConfig(): Promise<AuthConfig> {
  return apiFetch<AuthConfig>('/auth/config');
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>('/auth/me');
}
