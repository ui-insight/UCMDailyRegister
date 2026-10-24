import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { triggerAIEdit } from './aiEdits';

const fetchMock = vi.fn();

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  localStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('AI task polling through a restart', () => {
  it('keeps the accepted task ID after a dropped connection and shows interruption', async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json({ Task_Id: 'durable-task' }))
      .mockRejectedValueOnce(new TypeError('Synthetic connection interruption'))
      .mockResolvedValueOnce(Response.json({
        Status: 'failed', Error_Message: 'AI editing was interrupted by a server restart. Retry this edit.',
      }));
    const result = expect(triggerAIEdit('submission', 'tdr')).rejects.toThrow('interrupted');
    await vi.runAllTimersAsync();
    await result;
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls.slice(1).map(([url]) => url)).toEqual([
      '/api/v1/ai-edits/tasks/durable-task', '/api/v1/ai-edits/tasks/durable-task',
    ]);
  });

  it('recovers a completed result after a temporary gateway failure', async () => {
    const completed = { Edit_Version_Id: 'saved-version' };
    fetchMock
      .mockResolvedValueOnce(Response.json({ Task_Id: 'durable-task' }))
      .mockResolvedValueOnce(Response.json({ detail: 'Restarting' }, { status: 503 }))
      .mockResolvedValueOnce(Response.json({ Status: 'succeeded', Result: completed }));
    const result = triggerAIEdit('submission', 'tdr');
    await vi.runAllTimersAsync();
    expect(await result).toEqual(completed);
    expect(fetchMock.mock.calls.filter(([, options]) => options.method === 'POST')).toHaveLength(1);
  });

  it('stops immediately on denied status access', async () => {
    fetchMock
      .mockResolvedValueOnce(Response.json({ Task_Id: 'durable-task' }))
      .mockResolvedValueOnce(Response.json({ detail: 'Sign in again' }, { status: 401 }));
    await expect(triggerAIEdit('submission', 'tdr')).rejects.toThrow('Sign in again');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('does not automatically replay an edit request whose response was lost', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Synthetic connection interruption'));
    await expect(triggerAIEdit('submission', 'tdr')).rejects.toThrow('Unable to reach');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
