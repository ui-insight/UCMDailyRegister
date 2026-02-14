import { apiFetch } from './client';
import type { AIEditResponse, EditVersion } from '../types/aiEdit';

export async function triggerAIEdit(
  submissionId: string,
  newsletterType: 'tdr' | 'myui',
): Promise<AIEditResponse> {
  return apiFetch<AIEditResponse>(`/ai-edits/${submissionId}/edit`, {
    method: 'POST',
    body: JSON.stringify({ newsletter_type: newsletterType }),
  });
}

export async function listEditVersions(submissionId: string): Promise<EditVersion[]> {
  return apiFetch<EditVersion[]>(`/ai-edits/${submissionId}/versions`);
}

export async function getEditVersion(
  submissionId: string,
  versionId: string,
): Promise<EditVersion> {
  return apiFetch<EditVersion>(`/ai-edits/${submissionId}/versions/${versionId}`);
}

export async function saveEditorFinal(
  submissionId: string,
  data: { headline: string; body: string; headline_case?: string },
): Promise<EditVersion> {
  return apiFetch<EditVersion>(`/ai-edits/${submissionId}/finalize`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
