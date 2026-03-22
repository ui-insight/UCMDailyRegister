import { apiFetch } from './client';
import type {
  RecurringMessage,
  RecurringMessageIssueCandidate,
  RecurrenceType,
} from '../types/recurringMessage';

interface RecurringMessagePayload {
  Newsletter_Type: 'tdr' | 'myui';
  Section_Id: string;
  Headline: string;
  Body: string;
  Start_Date: string;
  Recurrence_Type: RecurrenceType;
  Recurrence_Interval: number;
  End_Date?: string | null;
  Is_Active?: boolean;
}

export async function listRecurringMessages(params?: {
  newsletter_type?: string;
  active_only?: boolean;
}): Promise<RecurringMessage[]> {
  const searchParams = new URLSearchParams();
  if (params?.newsletter_type) searchParams.set('newsletter_type', params.newsletter_type);
  if (params?.active_only) searchParams.set('active_only', 'true');
  const query = searchParams.toString();
  return apiFetch<RecurringMessage[]>(`/recurring-messages${query ? `?${query}` : ''}`);
}

export async function createRecurringMessage(
  data: RecurringMessagePayload,
): Promise<RecurringMessage> {
  return apiFetch<RecurringMessage>('/recurring-messages', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateRecurringMessage(
  id: string,
  data: Partial<RecurringMessagePayload>,
): Promise<RecurringMessage> {
  return apiFetch<RecurringMessage>(`/recurring-messages/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteRecurringMessage(id: string): Promise<void> {
  await apiFetch(`/recurring-messages/${id}`, { method: 'DELETE' });
}

export async function listRecurringMessageCandidates(
  newsletterId: string,
): Promise<RecurringMessageIssueCandidate[]> {
  return apiFetch<RecurringMessageIssueCandidate[]>(`/newsletters/${newsletterId}/recurring-messages`);
}

export async function addRecurringMessageToNewsletter(
  newsletterId: string,
  recurringMessageId: string,
): Promise<void> {
  await apiFetch(`/newsletters/${newsletterId}/recurring-messages/${recurringMessageId}`, {
    method: 'POST',
  });
}

export async function skipRecurringMessageForNewsletter(
  newsletterId: string,
  recurringMessageId: string,
): Promise<void> {
  await apiFetch(`/newsletters/${newsletterId}/recurring-messages/${recurringMessageId}/skip`, {
    method: 'POST',
  });
}
