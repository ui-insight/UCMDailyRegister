import { ApiError, apiFetch } from './client';
import type { AIEditResponse, AIEditTaskResponse, EditVersion } from '../types/aiEdit';

const AI_EDIT_POLL_INTERVAL_MS = 1500;
const AI_EDIT_MAX_POLLS = 120;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function triggerAIEdit(
  submissionId: string,
  newsletterType: 'tdr' | 'myui',
  editorInstructions?: string,
): Promise<AIEditResponse> {
  const task = await apiFetch<AIEditTaskResponse>(`/ai-edits/${submissionId}/edit`, {
    method: 'POST',
    body: JSON.stringify({
      Newsletter_Type: newsletterType,
      Editor_Instructions: editorInstructions?.trim() || null,
    }),
  });

  return pollAIEditTask(task.Task_Id);
}

export async function getAIEditTask(taskId: string): Promise<AIEditTaskResponse> {
  return apiFetch<AIEditTaskResponse>(`/ai-edits/tasks/${taskId}`);
}

async function pollAIEditTask(taskId: string): Promise<AIEditResponse> {
  let statusUnavailable = false;
  for (let attempt = 0; attempt < AI_EDIT_MAX_POLLS; attempt += 1) {
    let task: AIEditTaskResponse;
    try {
      task = await getAIEditTask(taskId);
      statusUnavailable = false;
    } catch (error) {
      // A restart can briefly interrupt status reads. Keep polling the same
      // durable ID; never repeat the POST that started the external AI work.
      const temporary = error instanceof ApiError
        ? [502, 503, 504].includes(error.status)
        : error instanceof Error && error.cause instanceof Error;
      if (!temporary) throw error;
      statusUnavailable = true;
      await wait(AI_EDIT_POLL_INTERVAL_MS);
      continue;
    }
    if (task.Status === 'succeeded' && task.Result) {
      return task.Result;
    }
    if (task.Status === 'failed') {
      throw new Error(task.Error_Message || 'AI edit failed');
    }
    await wait(AI_EDIT_POLL_INTERVAL_MS);
  }

  if (statusUnavailable) {
    throw new Error('Unable to check this AI edit right now. Reload and try again.');
  }
  throw new Error('AI edit is still running. Try again in a moment.');
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
  data: {
    Headline: string;
    Body: string;
    Headline_Case?: string;
    Approve_For_Newsletter?: boolean;
    Links?: Array<{
      Url: string;
      Anchor_Text?: string;
      Display_Order?: number;
    }>;
    /** Staff_Revision_Id the editor loaded; a newer save makes this a 409. */
    Base_Staff_Revision_Id?: string | null;
  },
): Promise<EditVersion> {
  return apiFetch<EditVersion>(`/ai-edits/${submissionId}/finalize`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
