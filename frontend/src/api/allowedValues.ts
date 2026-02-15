import { apiFetch } from './client';
import type { AllowedValue } from '../types/allowedValue';

export async function listAllowedValues(params?: {
  group?: string;
  active_only?: boolean;
}): Promise<AllowedValue[]> {
  const searchParams = new URLSearchParams();
  if (params?.group) searchParams.set('group', params.group);
  if (params?.active_only !== undefined) searchParams.set('active_only', String(params.active_only));
  const query = searchParams.toString();
  return apiFetch<AllowedValue[]>(`/allowed-values${query ? `?${query}` : ''}`);
}
