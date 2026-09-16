import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
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

function ShowLocation({ label }: { label: string }) {
  const location = useLocation();
  return <p>{label}: {location.pathname}{location.search}</p>;
}

function renderAt(hash: string) {
  window.history.replaceState(null, '', `/sso/callback${hash}`);
  return render(
    <MemoryRouter initialEntries={[`/sso/callback${hash}`]}>
      <Routes>
        <Route path="/sso/callback" element={<SsoCallbackPage />} />
        <Route path="/login" element={<ShowLocation label="login" />} />
        <Route path="/dashboard" element={<p>dashboard page</p>} />
        <Route path="/ops-triage" element={<p>ops page</p>} />
        <Route path="/slc-calendar" element={<p>slc page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

const future = Math.floor(Date.now() / 1000) + 3600;

describe('SsoCallbackPage', () => {
  beforeEach(() => {
    window.localStorage.clear();
    clearToken();
  });

  it('stores the token from the fragment and lands on the role home', async () => {
    const token = fakeJwt({ sub: 'a@uidaho.edu', name: 'A', role: 'ops', exp: future });
    renderAt(`#access_token=${token}`);

    await waitFor(() => expect(screen.getByText('ops page')).toBeInTheDocument());
    expect(getIdentity()?.role).toBe('ops');
    // The token must not stay in the address bar.
    expect(window.location.hash).toBe('');
    expect(window.localStorage.getItem('ucm_submitter_role')).toBe('ops');
  });

  it('honours next when the role may open it', async () => {
    const token = fakeJwt({ sub: 'a@uidaho.edu', name: 'A', role: 'staff', exp: future });
    renderAt(`#access_token=${token}&next=%2Fslc-calendar`);
    await waitFor(() => expect(screen.getByText('slc page')).toBeInTheDocument());
  });

  it('ignores next when the role may not open it', async () => {
    const token = fakeJwt({ sub: 'a@uidaho.edu', name: 'A', role: 'ops', exp: future });
    renderAt(`#access_token=${token}&next=%2Fdashboard`);
    await waitFor(() => expect(screen.getByText('ops page')).toBeInTheDocument());
  });

  it('hands a refusal to the login page with the reason', async () => {
    renderAt('#error=not_authorized');
    await waitFor(() => expect(screen.getByText(/^login:/)).toBeInTheDocument());
    expect(screen.getByText(/^login:/)).toHaveTextContent('/login?error=not_authorized');
    expect(getIdentity()).toBeNull();
    expect(window.location.hash).toBe('');
  });

  it('keeps next alongside the error so a retry lands in the right place', async () => {
    renderAt('#error=unavailable&next=%2Fops-triage');
    await waitFor(() => expect(screen.getByText(/^login:/)).toBeInTheDocument());
    expect(screen.getByText(/^login:/)).toHaveTextContent('error=unavailable&next=%2Fops-triage');
  });

  it('treats an empty fragment as a failed sign-in', async () => {
    renderAt('');
    await waitFor(() => expect(screen.getByText(/^login:/)).toBeInTheDocument());
    expect(screen.getByText(/^login:/)).toHaveTextContent('error=sign_in_failed');
  });
});
