import { apiFetch } from './client';
import type { NewsletterSection } from '../types/newsletter';

interface NewsletterResponse {
  Id: string;
  Newsletter_Type: 'tdr' | 'myui';
  Publish_Date: string;
  Status: string;
  Created_At: string;
  Updated_At: string;
}

export interface NewsletterItemResponse {
  Id: string;
  Newsletter_Id: string;
  Submission_Id: string;
  Section_Id: string;
  Position: number;
  Final_Headline: string;
  Final_Body: string;
  Run_Number: number;
}

export interface NewsletterDetailResponse extends NewsletterResponse {
  Items: NewsletterItemResponse[];
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
  Newsletter_Type: string;
  Publish_Date: string;
}): Promise<NewsletterResponse> {
  return apiFetch<NewsletterResponse>('/newsletters', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function assembleNewsletter(data: {
  Newsletter_Type: string;
  Publish_Date: string;
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
    Submission_Id: string;
    Section_Id: string;
    Position: number;
    Final_Headline: string;
    Final_Body: string;
    Run_Number?: number;
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
    Section_Id: string;
    Position: number;
    Final_Headline: string;
    Final_Body: string;
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
  positions: { Id: string; Position: number; Section_Id?: string }[],
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
