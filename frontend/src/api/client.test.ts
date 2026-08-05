import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from './client';

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
