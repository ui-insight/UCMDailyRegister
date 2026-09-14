import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { clearToken, getIdentity } from '../auth/tokenStore';
import SsoCallbackPage from './SsoCallbackPage';

function fakeJwt(claims: Record<string, unknown>): string {
  const b64 = (obj: unknown) => btoa(JSON.stringify(obj))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `${b64({ alg: 'HS256' })}.${b64(claims)}.sig`;
}

function renderAt(hash: string) {
  window.history.replaceState(null, '', `/sso/callback${hash}`);
  return render(
    <MemoryRouter initialEntries={[`/sso/callback${hash}`]}>
      <Routes>
        <Route path="/sso/callback" element={<SsoCallbackPage />} />
        <Route path="/dashboard" element={<p>dashboard page</p>} />
        <Route path="/ops-triage" element={<p>ops page</p>} />
        <Route path="/" element={<p>landing page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SsoCallbackPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
    clearToken();
  });

  it('stores the token from the fragment and lands on the role home', async () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const token = fakeJwt({ sub: 'a@uidaho.edu', name: 'A', role: 'ops', exp });
    renderAt(`#access_token=${token}`);

    await waitFor(() => expect(screen.getByText('ops page')).toBeInTheDocument());
    expect(getIdentity()?.role).toBe('ops');
    // The token must not stay in the address bar.
    expect(window.location.hash).toBe('');
    expect(window.localStorage.getItem('ucm_submitter_role')).toBe('ops');
  });

  it('explains not_authorized as a next step, not an error', () => {
    renderAt('#error=not_authorized');
    expect(screen.getByRole('heading')).toHaveTextContent("You're not set up for this app yet");
    expect(screen.getByText(/still submit items without signing in/)).toBeInTheDocument();
    expect(getIdentity()).toBeNull();
  });

  it('distinguishes an outage from a permission problem', () => {
    renderAt('#error=unavailable');
    expect(screen.getByText(/try again in a few minutes/)).toBeInTheDocument();
  });

  it('falls back for unknown or prototype-polluting reasons', () => {
    renderAt('#error=constructor');
    expect(screen.getByRole('heading')).toHaveTextContent("Sign-in didn't complete");
  });

  it('returns to the landing page from the button', async () => {
    renderAt('#error=sign_in_failed');
    screen.getByRole('button', { name: 'Back to start' }).click();
    await waitFor(() => expect(screen.getByText('landing page')).toBeInTheDocument());
  });
});
