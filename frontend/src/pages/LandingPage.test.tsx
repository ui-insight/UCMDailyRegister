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

  it('is one simple page with no menu of views', async () => {
    getAuthConfigMock.mockResolvedValue({ sso_enabled: true });
    renderApp();
    expect(
      screen.getByRole('heading', { level: 1, name: 'UCM Newsletter Submissions' }),
    ).toBeInTheDocument();
    expect(screen.getByText('The Daily Register')).toBeInTheDocument();
    expect(screen.getByText('My UI')).toBeInTheDocument();
    await screen.findByRole('button', { name: /Sign in with your University account/ });
    expect(screen.getAllByRole('button')).toHaveLength(1);
    expect(screen.queryByText(/\bviews?\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/SLC/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Event Services/)).not.toBeInTheDocument();
  });

  it('shows the next issue after today for each newsletter', async () => {
    getAuthConfigMock.mockResolvedValue({ sso_enabled: true });
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
    getAuthConfigMock.mockResolvedValue({ sso_enabled: true });
    getValidDatesMock.mockRejectedValue(new Error('offline'));
    renderApp();
    await waitFor(() => expect(getValidDatesMock).toHaveBeenCalled());
    expect(
      await screen.findByRole('button', { name: /Sign in with your University account/ }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('next-issue-tdr')).not.toBeInTheDocument();
  });

  describe('while the deployment mode is unknown', () => {
    it('keeps sign-in disabled until the backend answers', async () => {
      let answer: (value: { sso_enabled: boolean }) => void = () => {};
      getAuthConfigMock.mockReturnValue(
        new Promise((resolve) => {
          answer = resolve;
        }),
      );
      renderApp();
      const signIn = screen.getByRole('button', { name: /Sign in with your University account/ });
      expect(signIn).toBeDisabled();
      await userEvent.click(signIn);
      expect(assignSpy).not.toHaveBeenCalled();
      answer({ sso_enabled: true });
      await waitFor(() => expect(signIn).toBeEnabled());
    });

    it('offers a retry, not an anonymous form, when the check fails', async () => {
      getAuthConfigMock.mockRejectedValueOnce(new Error('offline'));
      getAuthConfigMock.mockResolvedValueOnce({ sso_enabled: true });
      renderApp();
      expect(await screen.findByRole('alert')).toHaveTextContent(/Sign-in isn't available/);
      expect(screen.queryByRole('button', { name: /Submit an item/ })).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /Sign in with your University account/ }),
      ).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
      const signIn = await screen.findByRole('button', {
        name: /Sign in with your University account/,
      });
      await waitFor(() => expect(signIn).toBeEnabled());
      expect(getAuthConfigMock).toHaveBeenCalledTimes(2);
    });
  });

  describe('SSO deployment', () => {
    beforeEach(() => {
      getAuthConfigMock.mockResolvedValue({ sso_enabled: true });
    });

    it('sends everyone to the University sign-in from one button', async () => {
      renderApp();
      const signIn = await screen.findByRole('button', {
        name: /Sign in with your University account/,
      });
      await waitFor(() => expect(signIn).toBeEnabled());
      await userEvent.click(signIn);
      expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/sso/login');
      expect(screen.queryByRole('button', { name: /Submit an item/ })).not.toBeInTheDocument();
    });

    it('sends a signed-in staff member straight to the dashboard', async () => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'staff', exp: future }));
      renderApp();
      expect(await screen.findByText('dashboard page')).toBeInTheDocument();
    });

    it('sends a signed-in submitter straight to the submission form', async () => {
      setToken(fakeJwt({ sub: 'p@uidaho.edu', name: 'Pat', role: 'submitter', exp: future }));
      renderApp();
      expect(await screen.findByText('submit page')).toBeInTheDocument();
    });

    it('sends an anonymous deep link to the submission form to sign in', async () => {
      renderApp('/submit');
      await waitFor(() => expect(screen.getByText(/^login:/)).toBeInTheDocument());
      expect(screen.getByText(/^login:/)).toHaveTextContent('/login?next=%2Fsubmit');
    });

    it('lets a signed-in submitter open the submission form', async () => {
      setToken(fakeJwt({ sub: 'p@uidaho.edu', name: 'Pat', role: 'submitter', exp: future }));
      renderApp('/submit');
      await waitFor(() => expect(getAuthConfigMock).toHaveBeenCalled());
      expect(screen.getByText('submit page')).toBeInTheDocument();
    });

    it('guards a deep link to a staff page for an anonymous visitor', async () => {
      renderApp('/dashboard');
      await waitFor(() => expect(screen.getByText(/^login:/)).toBeInTheDocument());
      expect(screen.getByText(/^login:/)).toHaveTextContent('/login?next=%2Fdashboard');
    });

    it.each(['slc', 'submitter'])('guards a staff page from a %s', async (role) => {
      setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role, exp: future }));
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

  describe('trusted-header deployment (SSO off, local development)', () => {
    beforeEach(() => {
      getAuthConfigMock.mockResolvedValue({ sso_enabled: false });
    });

    it('opens the staff workspace directly', async () => {
      renderApp();
      await userEvent.click(
        await screen.findByRole('button', { name: 'Open the staff workspace' }),
      );
      expect(screen.getByText('dashboard page')).toBeInTheDocument();
      expect(window.localStorage.getItem('ucm_submitter_role')).toBe('staff');
      expect(assignSpy).not.toHaveBeenCalled();
    });

    it('opens the submission form without signing in', async () => {
      renderApp();
      await userEvent.click(await screen.findByRole('button', { name: 'Submit an item' }));
      expect(screen.getByText('submit page')).toBeInTheDocument();
      expect(window.localStorage.getItem('ucm_submitter_role')).toBe('public');
    });
  });
});
