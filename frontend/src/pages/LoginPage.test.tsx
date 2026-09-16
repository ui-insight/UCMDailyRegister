import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getAuthConfig } from '../api/auth';
import { clearToken, setToken } from '../auth/tokenStore';
import { resetSsoEnabledCache } from '../auth/useAuth';
import LoginPage from './LoginPage';

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

function renderLogin(path = '/login') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<p>landing page</p>} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<p>dashboard page</p>} />
        <Route path="/slc-calendar" element={<p>slc page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  let assignSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    window.localStorage.clear();
    clearToken();
    resetSsoEnabledCache();
    getAuthConfigMock.mockResolvedValue({ sso_enabled: true });
    assignSpy = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, assign: assignSpy, pathname: '/login', search: '', hash: '' },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('redirects to Microsoft with no hint when the email is left blank', async () => {
    renderLogin();
    await userEvent.click(await screen.findByRole('button', { name: /Continue with Microsoft/ }));
    expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/sso/login');
  });

  it('forwards the email as a login hint and the destination as next', async () => {
    renderLogin('/login?next=%2Fslc-calendar');
    await userEvent.type(await screen.findByLabelText('University email'), 'jdoe@uidaho.edu');
    await userEvent.click(screen.getByRole('button', { name: /Continue with Microsoft/ }));
    expect(assignSpy).toHaveBeenCalledWith(
      '/api/v1/auth/sso/login?login_hint=jdoe%40uidaho.edu&next=%2Fslc-calendar',
    );
  });

  it('refuses to forward something that is not an email', async () => {
    renderLogin();
    await userEvent.type(await screen.findByLabelText('University email'), 'jdoe');
    await userEvent.click(screen.getByRole('button', { name: /Continue with Microsoft/ }));
    expect(assignSpy).not.toHaveBeenCalled();
    expect(screen.getByRole('status')).toHaveTextContent(/does not look like an email/);
  });

  it('nudges on a non-University domain but continues on the second try', async () => {
    renderLogin();
    await userEvent.type(await screen.findByLabelText('University email'), 'me@gmail.com');
    const button = screen.getByRole('button', { name: /Continue with Microsoft/ });
    await userEvent.click(button);
    expect(assignSpy).not.toHaveBeenCalled();
    expect(screen.getByRole('status')).toHaveTextContent(/@uidaho.edu/);
    await userEvent.click(button);
    expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/sso/login?login_hint=me%40gmail.com');
  });

  it('drops an unsafe next rather than forwarding it', async () => {
    renderLogin('/login?next=https%3A%2F%2Fevil.example');
    await userEvent.click(await screen.findByRole('button', { name: /Continue with Microsoft/ }));
    expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/sso/login');
  });

  it('explains a sign-in failure above the form', async () => {
    renderLogin('/login?error=not_authorized');
    expect(await screen.findByRole('alert')).toHaveTextContent("You're not set up for this app yet");
    expect(screen.getByRole('button', { name: /Continue with Microsoft/ })).toBeInTheDocument();
  });

  it('offers Continue and Sign out to an already signed-in user', async () => {
    setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'staff', exp: future }));
    renderLogin('/login?next=%2Fslc-calendar');
    expect(await screen.findByText('Sam')).toBeInTheDocument();
    expect(screen.queryByLabelText('University email')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.getByText('slc page')).toBeInTheDocument();
  });

  it('sends a signed-in user home when next is not permitted for their role', async () => {
    setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'slc', exp: future }));
    renderLogin('/login?next=%2Fdashboard');
    await userEvent.click(await screen.findByRole('button', { name: 'Continue' }));
    expect(screen.getByText('slc page')).toBeInTheDocument();
  });

  it('signs out through the backend', async () => {
    setToken(fakeJwt({ sub: 's@uidaho.edu', name: 'Sam', role: 'staff', exp: future }));
    renderLogin();
    await userEvent.click(await screen.findByRole('button', { name: 'Sign out' }));
    expect(assignSpy).toHaveBeenCalledWith('/api/v1/auth/logout');
    expect(window.localStorage.getItem('ucm_session_token')).toBeNull();
  });

  it('is not reachable under the trusted-header deployment', async () => {
    getAuthConfigMock.mockResolvedValue({ sso_enabled: false });
    renderLogin();
    await waitFor(() => expect(screen.getByText('landing page')).toBeInTheDocument());
  });
});
