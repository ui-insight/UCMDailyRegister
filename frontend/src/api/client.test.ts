import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from './client';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('apiFetch network failures', () => {
  it('turns an unreachable API into an actionable retry message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    await expect(apiFetch('/submissions')).rejects.toThrow(
      'Unable to reach the UCM service. Check your connection and retry.',
    );
  });
});

describe('apiFetch error responses', () => {
  it('keeps the status and structured detail, with a readable message', async () => {
    const detail = { message: 'Someone saved a newer version.', Current_Revision: { Id: 'v2' } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail }), { status: 409 }),
    ));

    const error = await apiFetch('/ai-edits/x/finalize').catch((err: unknown) => err);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, detail, message: 'Someone saved a newer version.' });
  });
});
