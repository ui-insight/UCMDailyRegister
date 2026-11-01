import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getAuthConfig } from '../api/auth';
import { getValidDates } from '../api/schedule';
import { clearToken, setToken } from '../auth/tokenStore';
import { resetSsoEnabledCache } from '../auth/useAuth';
import RequireRole from '../auth/RequireRole';
import { addDaysISO, formatAPDate, todayISO } from '../utils/date';
import LandingPage from './LandingPage';

function ShowLocation({ label }: { label: string }) {
  const location = useLocation();
  return <p>{label}: {location.pathname}{location.search}</p>;
}

vi.mock('../api/auth', async () => {
  const actual = await vi.importActual<typeof import('../api/auth')>('../api/auth');
  return { ...actual, getAuthConfig: vi.fn() };
});

vi.mock('../api/schedule', () => ({ getValidDates: vi.fn() }));

const getAuthConfigMock = vi.mocked(getAuthConfig);
const getValidDatesMock = vi.mocked(getValidDates);

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
        <Route path="/login" element={<ShowLocation label="login" />} />
        <Route element={<RequireRole />}>
          <Route path="/submit" element={<p>submit page</p>} />
          <Route path="/dashboard" element={<p>dashboard page</p>} />
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
    getValidDatesMock.mockResolvedValue({ dates: [], blackout_dates: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('describes both newsletters and leaves out the hidden SLC and Event Services views', async () => {
    getAuthConfigMock.mockResolvedValue({ sso_enabled: false });
    renderApp();
    await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: 'The Daily Register' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'My UI' })).toBeInTheDocument();
    expect(screen.queryByText(/SLC/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Event Services/)).not.toBeInTheDocument();
  });

  it('shows the next issue after today for each newsletter', async () => {
    getAuthConfigMock.mockResolvedValue({ sso_enabled: false });
    const tomorrow = addDaysISO(1);
    const inThreeDays = addDaysISO(3);
    getValidDatesMock.mockResolvedValue({
      dates: [
        { date: todayISO(), newsletters: ['tdr', 'myui'] },
        { date: tomorrow, newsletters: ['tdr'] },
        { date: inThreeDays, newsletters: ['tdr', 'myui'] },
      ],
      blackout_dates: [],
    });
    renderApp();
    expect(await screen.findByTestId('next-issue-tdr')).toHaveTextContent(formatAPDate(tomorrow));
    expect(screen.getByTestId('next-issue-myui')).toHaveTextContent(formatAPDate(inThreeDays));
  });

  it('still renders when the schedule cannot be loaded', async () => {
    getAuthConfigMock.mockResolvedValue({ sso_enabled: false });
    getValidDatesMock.mockRejectedValue(new Error('offline'));
    renderApp();
    await waitFor(() => expect(getValidDatesMock).toHaveBeenCalled());
    expect(screen.getByRole('button', { name: /Submit an item/ })).toBeInTheDocument();
    expect(screen.queryByTestId('next-issue-tdr')).not.toBeInTheDocument();
  });

  describe('trusted-header deployment (SSO off)', () => {
    beforeEach(() => {
      getAuthConfigMock.mockResolvedValue({ sso_enabled: false });
    });

    it('opens the staff workspace directly, as today', async () => {
      renderApp();
      await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
      await userEvent.click(screen.getByRole('button', { name: 'Open the staff workspace' }));
      expect(screen.getByText('dashboard page')).toBeInTheDocument();
      expect(window.localStorage.getItem('ucm_submitter_role')).toBe('staff');
      expect(assignSpy).not.toHaveBeenCalled();
    });

    it('opens the submission form', async () => {
      renderApp();
      await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
      await userEvent.click(screen.getByRole('button', { name: /Submit an item/ }));
      expect(screen.getByText('submit page')).toBeInTheDocument();
      expect(window.localStorage.getItem('ucm_submitter_role')).toBe('public');
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

    it('sends an anonymous visitor to the login page, remembering the dashboard', async () => {
      renderApp();
      await userEvent.click(await screen.findByRole('button', { name: 'Staff sign in' }));
      expect(screen.getByText(/^login:/)).toHaveTextContent('/login?next=%2Fdashboard');
      expect(assignSpy).not.toHaveBeenCalled();
    });

    it('still lets an anonymous visitor submit an item', async () => {
      renderApp();
      await screen.findByRole('button', { name: 'Staff sign in' });
      await userEvent.click(screen.getByRole('button', { name: /Submit an item/ }));
      expect(screen.getByText('submit page')).toBeInTheDocument();
      expect(assignSpy).not.toHaveBeenCalled();
    });

    it('lets a signed-in staff member go straight to the dashboard', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'staff', exp: future }));
      renderApp();
      expect(await screen.findByTestId('sign-in-status')).toHaveTextContent('Signed in as Sam');
      await userEvent.click(screen.getByRole('button', { name: 'Go to dashboard' }));
      expect(screen.getByText('dashboard page')).toBeInTheDocument();
    });

    it('sends a signed-in SLC member to the login page instead of the dashboard', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'slc', exp: future }));
      renderApp();
      await userEvent.click(await screen.findByRole('button', { name: 'Staff sign in' }));
      expect(screen.getByText(/^login:/)).toHaveTextContent('/login?next=%2Fdashboard');
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
      // known to be on and there is no identity, it redirects to sign-in.
      await waitFor(() => expect(screen.getByText(/^login:/)).toBeInTheDocument());
      expect(screen.getByText(/^login:/)).toHaveTextContent('/login?next=%2Fdashboard');
    });

    it('guards a deep link to a staff page for an SLC member', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'slc', exp: future }));
      renderApp('/dashboard');
      await waitFor(() => expect(screen.getByText(/^login:/)).toBeInTheDocument());
    });

    it('lets a staff member through a deep link', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'staff', exp: future }));
      renderApp('/dashboard');
      await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
      expect(screen.getByText('dashboard page')).toBeInTheDocument();
    });
  });
});
