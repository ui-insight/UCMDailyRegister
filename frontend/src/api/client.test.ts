import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiDownload, apiFetch, filenameFromDisposition } from './client';
import { clearToken, setToken } from '../auth/tokenStore';

afterEach(() => {
  vi.unstubAllGlobals();
  clearToken();
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


describe('apiDownload', () => {
  it('sends the SSO bearer token and returns the file with its name (#476)', async () => {
    const claims = { sub: 'synthetic', name: 'Synthetic Staff', role: 'staff', exp: Date.now() / 1000 + 3600 };
    const token = `x.${btoa(JSON.stringify(claims))}.y`;
    setToken(token);
    const fetchMock = vi.fn().mockResolvedValue(new Response('docx-bytes', {
      status: 200,
      headers: { 'Content-Disposition': 'attachment; filename="tdr_2026-11-16.docx"' },
    }));
    vi.stubGlobal('fetch', fetchMock);

    const file = await apiDownload('/newsletters/n1/export');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/newsletters/n1/export', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: `Bearer ${token}` }),
    }));
    expect(file.filename).toBe('tdr_2026-11-16.docx');
    expect(await file.blob.text()).toBe('docx-bytes');
  });

  it('raises the API error instead of returning an error body as a file', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Staff access required' }), { status: 403 }),
    ));

    await expect(apiDownload('/newsletters/n1/export')).rejects.toMatchObject({
      status: 403,
      message: 'Staff access required',
    });
    await expect(apiDownload('/newsletters/n1/export')).rejects.toBeInstanceOf(ApiError);
  });

  it('reads plain and encoded filenames', () => {
    expect(filenameFromDisposition('attachment; filename="a b.docx"')).toBe('a b.docx');
    expect(filenameFromDisposition("attachment; filename*=UTF-8''my%20ui.docx")).toBe('my ui.docx');
    expect(filenameFromDisposition(null)).toBeNull();
  });
});
