import { apiFetch } from './client';
import type {
  BlackoutDate,
  CustomPublishDate,
  ScheduleModeOverride,
  ValidDatesResponse,
} from '../types/schedule';

export async function getValidDates(
  from: string,
  to: string,
  newsletterType?: string,
): Promise<ValidDatesResponse> {
  const params = new URLSearchParams({ from, to });
  if (newsletterType) params.set('newsletter_type', newsletterType);
  return apiFetch<ValidDatesResponse>(`/schedule/valid-dates?${params}`);
}

// --- Blackout dates ---

export async function getBlackoutDates(newsletterType?: string): Promise<BlackoutDate[]> {
  const params = newsletterType ? `?newsletter_type=${newsletterType}` : '';
  return apiFetch<BlackoutDate[]>(`/schedule/blackout-dates${params}`);
}

export async function createBlackoutDate(data: {
  Blackout_Date: string;
  Newsletter_Type?: string | null;
  Description?: string | null;
}): Promise<BlackoutDate> {
  return apiFetch<BlackoutDate>('/schedule/blackout-dates', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteBlackoutDate(id: string): Promise<void> {
  return apiFetch<void>(`/schedule/blackout-dates/${id}`, { method: 'DELETE' });
}

// --- Mode overrides ---

export async function getModeOverrides(newsletterType?: string): Promise<ScheduleModeOverride[]> {
  const params = newsletterType ? `?newsletter_type=${newsletterType}` : '';
  return apiFetch<ScheduleModeOverride[]>(`/schedule/mode-overrides${params}`);
}

export async function createModeOverride(data: {
  Newsletter_Type: string;
  Override_Mode: string;
  Start_Date: string;
  End_Date: string;
  Description?: string | null;
}): Promise<ScheduleModeOverride> {
  return apiFetch<ScheduleModeOverride>('/schedule/mode-overrides', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteModeOverride(id: string): Promise<void> {
  return apiFetch<void>(`/schedule/mode-overrides/${id}`, { method: 'DELETE' });
}

// --- Custom publish dates ---

export async function getCustomDates(newsletterType?: string): Promise<CustomPublishDate[]> {
  const params = newsletterType ? `?newsletter_type=${newsletterType}` : '';
  return apiFetch<CustomPublishDate[]>(`/schedule/custom-dates${params}`);
}

export async function createCustomDate(data: {
  Newsletter_Type: string;
  Publish_Date: string;
  Description?: string | null;
}): Promise<CustomPublishDate> {
  return apiFetch<CustomPublishDate>('/schedule/custom-dates', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteCustomDate(id: string): Promise<void> {
  return apiFetch<void>(`/schedule/custom-dates/${id}`, { method: 'DELETE' });
}
