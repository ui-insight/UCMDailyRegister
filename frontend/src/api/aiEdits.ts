import { apiFetch } from './client';
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
  for (let attempt = 0; attempt < AI_EDIT_MAX_POLLS; attempt += 1) {
    const task = await getAIEditTask(taskId);
    if (task.Status === 'succeeded' && task.Result) {
      return task.Result;
    }
    if (task.Status === 'failed') {
      throw new Error(task.Error_Message || 'AI edit failed');
    }
    await wait(AI_EDIT_POLL_INTERVAL_MS);
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
  data: { Headline: string; Body: string; Headline_Case?: string },
): Promise<EditVersion> {
  return apiFetch<EditVersion>(`/ai-edits/${submissionId}/finalize`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
