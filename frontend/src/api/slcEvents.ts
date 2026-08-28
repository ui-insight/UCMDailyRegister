import { apiFetch } from './client';
import type {
  HarvestedEvent,
  HarvestedEventListResponse,
  HarvestedEventUpdate,
  HarvestSummary,
} from '../types/harvestedEvent';

export async function listHarvestedEvents(params?: {
  date_from?: string;
  date_to?: string;
  category?: string;
  review_status?: string;
  offset?: number;
  limit?: number;
}): Promise<HarvestedEventListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return apiFetch<HarvestedEventListResponse>(
    `/slc/harvested-events${query ? `?${query}` : ''}`,
  );
}

export async function runHarvest(): Promise<HarvestSummary> {
  return apiFetch<HarvestSummary>('/slc/harvest', { method: 'POST' });
}

export async function updateHarvestedEvent(
  id: string,
  data: HarvestedEventUpdate,
): Promise<HarvestedEvent> {
  return apiFetch<HarvestedEvent>(`/slc/harvested-events/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
