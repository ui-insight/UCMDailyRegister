import { apiFetch } from './client';
import type {
  OpsEvent,
  OpsEventListResponse,
  OpsEventUpdate,
  OpsNeedVerdict,
} from '../types/harvestedEvent';

export async function listOpsEvents(params?: {
  date_from?: string;
  date_to?: string;
  category?: string;
  review_status?: string;
  need?: string;
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

export async function updateOpsEvent(
  id: string,
  data: OpsEventUpdate,
): Promise<OpsEvent> {
  return apiFetch<OpsEvent>(`/ops/harvested-events/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function addOpsNeed(id: string, need: string): Promise<OpsEvent> {
  return apiFetch<OpsEvent>(`/ops/harvested-events/${id}/needs`, {
    method: 'POST',
    body: JSON.stringify({ Need: need }),
  });
}

export async function setOpsNeedVerdict(
  id: string,
  need: string,
  verdict: OpsNeedVerdict,
): Promise<OpsEvent> {
  return apiFetch<OpsEvent>(`/ops/harvested-events/${id}/needs/${need}`, {
    method: 'PATCH',
    body: JSON.stringify({ Verdict: verdict }),
  });
}

export async function removeOpsNeed(id: string, need: string): Promise<OpsEvent> {
  return apiFetch<OpsEvent>(`/ops/harvested-events/${id}/needs/${need}`, {
    method: 'DELETE',
  });
}
