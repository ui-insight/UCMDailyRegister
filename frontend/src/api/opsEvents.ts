import { apiFetch } from './client';
import type { OpsEventListResponse } from '../types/harvestedEvent';

export async function listOpsEvents(params?: {
  date_from?: string;
  date_to?: string;
  category?: string;
  review_status?: string;
  offset?: number;
  limit?: number;
}): Promise<OpsEventListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return apiFetch<OpsEventListResponse>(
    `/ops/harvested-events${query ? `?${query}` : ''}`,
  );
}
