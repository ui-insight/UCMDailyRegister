import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  apiDownload,
  apiFetch,
  apiUpload,
  filenameFromDisposition,
  saveDownloadedFile,
} from './client';
import { downloadNewsletterExport } from './newsletters';
import { clearToken, getToken, setToken } from '../auth/tokenStore';

function signInAsStaff(): string {
  const claims = { sub: 'synthetic', name: 'Synthetic Staff', role: 'staff', exp: Date.now() / 1000 + 3600 };
  const token = `x.${btoa(JSON.stringify(claims))}.y`;
  setToken(token);
  return token;
}

function sentHeaders(fetchMock: ReturnType<typeof vi.fn>, call = 0): Headers {
  return new Headers(fetchMock.mock.calls[call][1].headers);
}

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
    const token = signInAsStaff();
    const fetchMock = vi.fn().mockResolvedValue(new Response('docx-bytes', {
      status: 200,
      headers: { 'Content-Disposition': 'attachment; filename="tdr_2026-11-16.docx"' },
    }));
    vi.stubGlobal('fetch', fetchMock);

    const file = await apiDownload('/newsletters/n1/export');

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/newsletters/n1/export');
    expect(sentHeaders(fetchMock).get('Authorization')).toBe(`Bearer ${token}`);
    expect(sentHeaders(fetchMock).get('Content-Type')).toBeNull();
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


describe('credentials are never dropped', () => {
  it.each([
    ['an object', { Accept: 'application/json' }],
    ['a Headers instance', new Headers({ Accept: 'application/json' })],
    ['tuples', [['Accept', 'application/json']] as [string, string][]],
  ])('keeps the bearer token and JSON type when the caller passes %s', async (_label, headers) => {
    const token = signInAsStaff();
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/newsletters', { headers });

    const sent = sentHeaders(fetchMock);
    expect(sent.get('Authorization')).toBe(`Bearer ${token}`);
    expect(sent.get('Content-Type')).toBe('application/json');
    expect(sent.get('Accept')).toBe('application/json');
  });

  it('uploads form data with the token and lets the browser set the multipart type', async () => {
    const token = signInAsStaff();
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"Id":"s1"}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const body = new FormData();
    body.append('file', new Blob(['x']), 'x.png');

    await expect(apiUpload('/submissions/s1/image', body)).resolves.toEqual({ Id: 's1' });

    expect(sentHeaders(fetchMock).get('Authorization')).toBe(`Bearer ${token}`);
    expect(sentHeaders(fetchMock).get('Content-Type')).toBeNull();
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', body });
  });

  it('exports a newsletter through the authenticated download', async () => {
    const token = signInAsStaff();
    const fetchMock = vi.fn().mockResolvedValue(new Response('docx', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await downloadNewsletterExport('n1');

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/newsletters/n1/export');
    expect(sentHeaders(fetchMock).get('Authorization')).toBe(`Bearer ${token}`);
  });

  it('signs out when a download is refused with 401', async () => {
    signInAsStaff();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not json', { status: 401 })));

    await expect(apiDownload('/newsletters/n1/export')).rejects.toMatchObject({ status: 401 });
    expect(getToken()).toBeNull();
  });
});

describe('saveDownloadedFile', () => {
  it('saves under the server name and releases the object URL', async () => {
    vi.useFakeTimers();
    const createObjectURL = vi.fn().mockReturnValue('blob:synthetic');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', Object.assign(Object.create(URL), { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    saveDownloadedFile({ blob: new Blob(['x']), filename: 'tdr_2026-11-16.docx' }, 'fallback.docx');

    const link = click.mock.contexts[0] as HTMLAnchorElement;
    expect(link.download).toBe('tdr_2026-11-16.docx');
    expect(link.isConnected).toBe(false);
    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:synthetic');
    click.mockRestore();
    vi.useRealTimers();
  });
});
