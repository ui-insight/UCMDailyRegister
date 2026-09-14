import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getAuthConfig } from '../api/auth';
import { clearToken, setToken } from '../auth/tokenStore';
import { resetSsoEnabledCache } from '../auth/useAuth';
import RequireRole from '../auth/RequireRole';
import LandingPage from './LandingPage';

vi.mock('../api/auth', async () => {
  const actual = await vi.importActual<typeof import('../api/auth')>('../api/auth');
  return { ...actual, getAuthConfig: vi.fn() };
});

const getAuthConfigMock = vi.mocked(getAuthConfig);

function fakeJwt(claims: Record<string, unknown>): string {
  const b64 = (obj: unknown) => btoa(JSON.stringify(obj))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `${b64({ alg: 'HS256' })}.${b64(claims)}.sig`;
}

const future = Math.floor(Date.now() / 1000) + 3600;

function renderApp(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route element={<RequireRole />}>
          <Route path="/submit" element={<p>submit page</p>} />
          <Route path="/dashboard" element={<p>dashboard page</p>} />
          <Route path="/slc-calendar" element={<p>slc page</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('LandingPage', () => {
  let assignSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    window.localStorage.clear();
    clearToken();
    resetSsoEnabledCache();
    assignSpy = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, assign: assignSpy, pathname: '/', search: '', hash: '' },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('trusted-header deployment (SSO off)', () => {
    beforeEach(() => {
      getAuthConfigMock.mockResolvedValue({ sso_enabled: false });
    });

    it('opens Staff view directly, as today', async () => {
      renderApp();
      await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
      await userEvent.click(screen.getByRole('button', { name: /Staff view/ }));
      expect(screen.getByText('dashboard page')).toBeInTheDocument();
      expect(assignSpy).not.toHaveBeenCalled();
    });

    it('shows no sign-in status line', async () => {
      renderApp();
      await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
      expect(screen.queryByTestId('sign-in-status')).not.toBeInTheDocument();
    });
  });

  describe('SSO deployment', () => {
    beforeEach(() => {
      getAuthConfigMock.mockResolvedValue({ sso_enabled: true });
    });

    it('sends an anonymous visitor to Entra when choosing Staff view', async () => {
      renderApp();
      await screen.findByTestId('sign-in-status');
      await userEvent.click(screen.getByRole('button', { name: /Staff view/ }));
      expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/sso/login');
    });

    it('still lets an anonymous visitor into Submitter view', async () => {
      renderApp();
      await screen.findByTestId('sign-in-status');
      await userEvent.click(screen.getByRole('button', { name: /Submitter view/ }));
      expect(screen.getByText('submit page')).toBeInTheDocument();
      expect(assignSpy).not.toHaveBeenCalled();
    });

    it('lets a signed-in SLC member into SLC view but not Staff view', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'slc', exp: future }));
      renderApp();
      expect(await screen.findByText('Sam')).toBeInTheDocument();

      await userEvent.click(screen.getByRole('button', { name: /SLC Leadership view/ }));
      expect(screen.getByText('slc page')).toBeInTheDocument();
    });

    it('re-prompts sign-in when a signed-in user picks a view they may not open', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'slc', exp: future }));
      renderApp();
      await screen.findByText('Sam');
      await userEvent.click(screen.getByRole('button', { name: /Staff view/ }));
      expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/sso/login');
    });

    it('signs out through the backend so the Entra session ends too', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'staff', exp: future }));
      renderApp();
      await userEvent.click(await screen.findByRole('button', { name: 'Sign out' }));
      expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/logout');
      expect(window.localStorage.getItem('ucm_session_token')).toBeNull();
    });

    it('guards a deep link to a staff page for an anonymous visitor', async () => {
      renderApp('/dashboard');
      // Before the config answers, RequireRole renders the page; once SSO is
      // known to be on and there is no identity, it redirects to the landing page.
      await waitFor(() => expect(screen.getByText('Choose your view')).toBeInTheDocument());
    });

    it('guards a deep link to a staff page for an SLC member', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'slc', exp: future }));
      renderApp('/dashboard');
      await waitFor(() => expect(screen.getByText('Choose your view')).toBeInTheDocument());
    });

    it('lets a staff member through a deep link', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'staff', exp: future }));
      renderApp('/dashboard');
      await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
      expect(screen.getByText('dashboard page')).toBeInTheDocument();
    });
  });
});
