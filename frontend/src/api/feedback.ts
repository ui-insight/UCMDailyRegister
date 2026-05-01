import { apiFetch } from './client';
import type {
  FeedbackStatus,
  FeedbackType,
  ProductFeedback,
  ProductFeedbackCreate,
  ProductFeedbackExport,
} from '../types/feedback';

export async function createFeedback(
  data: ProductFeedbackCreate,
): Promise<ProductFeedback> {
  return apiFetch<ProductFeedback>('/feedback', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function listFeedback(params?: {
  status?: FeedbackStatus | '';
  feedback_type?: FeedbackType | '';
}): Promise<ProductFeedback[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.feedback_type) searchParams.set('feedback_type', params.feedback_type);
  const query = searchParams.toString();
  return apiFetch<ProductFeedback[]>(`/feedback${query ? `?${query}` : ''}`);
}

export async function updateFeedback(
  id: string,
  data: Partial<Pick<ProductFeedback, 'Status' | 'GitHub_URL'>>,
): Promise<ProductFeedback> {
  return apiFetch<ProductFeedback>(`/feedback/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function getFeedbackGitHubExport(
  id: string,
): Promise<ProductFeedbackExport> {
  return apiFetch<ProductFeedbackExport>(`/feedback/${id}/github-export`);
}
