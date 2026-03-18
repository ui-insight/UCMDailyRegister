import { apiFetch } from './client';
import type { ValidDatesResponse } from '../types/schedule';

export async function getValidDates(
  from: string,
  to: string,
  newsletterType?: string,
): Promise<ValidDatesResponse> {
  const params = new URLSearchParams({ from, to });
  if (newsletterType) params.set('newsletter_type', newsletterType);
  return apiFetch<ValidDatesResponse>(`/schedule/valid-dates?${params}`);
}
