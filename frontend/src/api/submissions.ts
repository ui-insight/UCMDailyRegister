import { apiFetch } from './client';
import type { Submission, SubmissionCreate } from '../types/submission';

interface SubmissionListResponse {
  Items: Submission[];
  Total: number;
}

export async function createSubmission(data: SubmissionCreate): Promise<Submission> {
  return apiFetch<Submission>('/submissions/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function listSubmissions(params?: {
  status?: string;
  category?: string;
  target_newsletter?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  offset?: number;
  limit?: number;
}): Promise<SubmissionListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return apiFetch<SubmissionListResponse>(`/submissions/${query ? `?${query}` : ''}`);
}

export async function getSubmission(id: string): Promise<Submission> {
  return apiFetch<Submission>(`/submissions/${id}`);
}

export async function updateSubmission(
  id: string,
  data: Partial<Submission>,
): Promise<Submission> {
  return apiFetch<Submission>(`/submissions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteSubmission(id: string): Promise<void> {
  await apiFetch(`/submissions/${id}`, { method: 'DELETE' });
}

export async function uploadImage(submissionId: string, file: File): Promise<Submission> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`/api/v1/submissions/${submissionId}/image`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || res.statusText);
  }
  return res.json();
}
