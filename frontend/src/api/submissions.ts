import { apiFetch, formatApiError } from './client';
import type { Submission, SubmissionCreate, SubmissionScheduleRequest } from '../types/submission';
import { getSubmitterRoleHeaders } from '../utils/submitterRole';

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
  slc_calendar_only?: boolean;
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

export async function skipScheduleOccurrence(
  submissionId: string,
  scheduleId: string,
  occurrenceDate: string,
): Promise<SubmissionScheduleRequest> {
  return apiFetch<SubmissionScheduleRequest>(
    `/submissions/${submissionId}/schedule/${scheduleId}/skip`,
    {
      method: 'POST',
      body: JSON.stringify({ Occurrence_Date: occurrenceDate }),
    },
  );
}

export async function rescheduleScheduleOccurrence(
  submissionId: string,
  scheduleId: string,
  occurrenceDate: string,
  newDate: string,
): Promise<SubmissionScheduleRequest> {
  return apiFetch<SubmissionScheduleRequest>(
    `/submissions/${submissionId}/schedule/${scheduleId}/reschedule`,
    {
      method: 'POST',
      body: JSON.stringify({
        Occurrence_Date: occurrenceDate,
        New_Date: newDate,
      }),
    },
  );
}

export async function addScheduleRequest(
  submissionId: string,
  data: { Requested_Date: string; Second_Requested_Date?: string },
): Promise<SubmissionScheduleRequest> {
  return apiFetch<SubmissionScheduleRequest>(
    `/submissions/${submissionId}/schedule`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  );
}

export async function uploadImage(submissionId: string, file: File): Promise<Submission> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`/api/v1/submissions/${submissionId}/image`, {
    method: 'POST',
    body: formData,
    headers: getSubmitterRoleHeaders(),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(formatApiError(error.detail ?? error));
  }
  return res.json();
}
