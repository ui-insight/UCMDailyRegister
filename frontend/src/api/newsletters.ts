import { apiFetch } from './client';
import type { NewsletterSection } from '../types/newsletter';

interface NewsletterResponse {
  id: string;
  newsletter_type: 'tdr' | 'myui';
  publish_date: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface NewsletterItemResponse {
  id: string;
  newsletter_id: string;
  submission_id: string;
  section_id: string;
  position: number;
  final_headline: string;
  final_body: string;
  run_number: number;
}

export interface NewsletterDetailResponse extends NewsletterResponse {
  items: NewsletterItemResponse[];
}

export async function listNewsletters(params?: {
  newsletter_type?: string;
  status?: string;
}): Promise<NewsletterResponse[]> {
  const searchParams = new URLSearchParams();
  if (params?.newsletter_type) searchParams.set('newsletter_type', params.newsletter_type);
  if (params?.status) searchParams.set('status', params.status);
  const query = searchParams.toString();
  return apiFetch<NewsletterResponse[]>(`/newsletters${query ? `?${query}` : ''}`);
}

export async function getNewsletter(id: string): Promise<NewsletterDetailResponse> {
  return apiFetch<NewsletterDetailResponse>(`/newsletters/${id}`);
}

export async function createNewsletter(data: {
  newsletter_type: string;
  publish_date: string;
}): Promise<NewsletterResponse> {
  return apiFetch<NewsletterResponse>('/newsletters', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function assembleNewsletter(data: {
  newsletter_type: string;
  publish_date: string;
}): Promise<NewsletterDetailResponse> {
  return apiFetch<NewsletterDetailResponse>('/newsletters/assemble', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateNewsletterStatus(
  id: string,
  status: string,
): Promise<NewsletterResponse> {
  return apiFetch<NewsletterResponse>(`/newsletters/${id}/status?status=${status}`, {
    method: 'PATCH',
  });
}

export async function addNewsletterItem(
  newsletterId: string,
  data: {
    submission_id: string;
    section_id: string;
    position: number;
    final_headline: string;
    final_body: string;
    run_number?: number;
  },
): Promise<NewsletterItemResponse> {
  return apiFetch<NewsletterItemResponse>(`/newsletters/${newsletterId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateNewsletterItem(
  newsletterId: string,
  itemId: string,
  data: Partial<{
    section_id: string;
    position: number;
    final_headline: string;
    final_body: string;
  }>,
): Promise<NewsletterItemResponse> {
  return apiFetch<NewsletterItemResponse>(`/newsletters/${newsletterId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function removeNewsletterItem(
  newsletterId: string,
  itemId: string,
): Promise<void> {
  await apiFetch(`/newsletters/${newsletterId}/items/${itemId}`, { method: 'DELETE' });
}

export async function reorderNewsletterItems(
  newsletterId: string,
  positions: { id: string; position: number; section_id?: string }[],
): Promise<void> {
  await apiFetch(`/newsletters/${newsletterId}/reorder`, {
    method: 'PUT',
    body: JSON.stringify(positions),
  });
}

export function getExportUrl(newsletterId: string): string {
  return `/api/v1/newsletters/${newsletterId}/export`;
}

export async function listSections(newsletterType?: string): Promise<NewsletterSection[]> {
  const query = newsletterType ? `?newsletter_type=${newsletterType}` : '';
  return apiFetch<NewsletterSection[]>(`/sections${query}`);
}
