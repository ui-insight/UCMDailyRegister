import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { SSO_LOGIN_URL, SSO_LOGOUT_URL } from '../api/auth';
import { clearToken } from '../auth/tokenStore';
import { useIdentity, useSsoEnabled } from '../auth/useAuth';
import { signInMessageFor } from '../auth/signInMessages';
import { homeForRole, roleMayOpen, setSubmitterRole } from '../utils/submitterRole';

const UI_DOMAIN = 'uidaho.edu';

/** Loose shape check only: the address is a hint to Microsoft, never a credential. */
function looksLikeEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

/** Microsoft's four-square mark, inline so the page needs no external assets. */
function MicrosoftMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 21 21" className="h-4 w-4 shrink-0">
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  );
}

/**
 * Sign-in entry for the Staff, SLC, and Event Services views.
 *
 * The password is never entered here. The optional email field is forwarded
 * to Microsoft as a `login_hint`, so the University sign-in page opens with
 * that account pre-filled; left blank, Microsoft shows its account picker.
 * `next` (an in-app path) rides through the backend so the user lands where
 * they were headed once Entra returns.
 *
 * Reached only when SSO is on: under the trusted-header deployment the
 * landing page cards go straight to their views, as they always have.
 */
export default function LoginPage() {
  const ssoEnabled = useSsoEnabled();
  const identity = useIdentity();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = searchParams.get('next');
  const error = searchParams.get('error');
  const [email, setEmail] = useState('');
  const [hint, setHint] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (ssoEnabled === false) {
    // Header-mode deployment: there is nothing to sign in to.
    return <Navigate to="/" replace />;
  }

  const destination = next && next.startsWith('/') && !next.startsWith('//') ? next : null;
  const message = error ? signInMessageFor(error) : null;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = email.trim();
    if (trimmed && !looksLikeEmail(trimmed)) {
      setHint('That does not look like an email address. Leave it blank to pick your account on the next screen.');
      return;
    }
    if (trimmed && !trimmed.toLowerCase().endsWith(`@${UI_DOMAIN}`) && hint === null) {
      // A nudge, not a block: some people sign in with an alias domain.
      setHint(`Most University accounts end in @${UI_DOMAIN}. Continue anyway, or fix the address.`);
      return;
    }
    setSubmitting(true);
    const params = new URLSearchParams();
    if (trimmed) params.set('login_hint', trimmed);
    if (destination) params.set('next', destination);
    const query = params.toString();
    window.location.assign(query ? `${SSO_LOGIN_URL}?${query}` : SSO_LOGIN_URL);
  };

  const handleContinue = () => {
    if (!identity) return;
    setSubmitterRole(identity.role);
    const target = destination && roleMayOpen(identity.role, destination)
      ? destination
      : homeForRole(identity.role);
    navigate(target, { replace: true });
  };

  const handleSignOut = () => {
    clearToken();
    window.location.assign(SSO_LOGOUT_URL);
  };

  return (
    <div className="min-h-screen bg-white">
      <header className="bg-gray-900">
        <div className="mx-auto max-w-3xl px-6 py-4">
          <img
            src="/ui-logo-gold-white-horizontal.png"
            alt="University of Idaho"
            className="h-8 w-auto"
          />
        </div>
      </header>

      <main className="mx-auto max-w-md px-6 py-16">
        <div className="rounded-lg border border-gray-200 bg-white px-8 py-10 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-ui-silver">
            UCM Newsletter Builder
          </p>

          {identity ? (
            <>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ui-black">
                You're signed in
              </h1>
              <p className="mt-3 text-sm text-ui-silver">
                Signed in as <span className="font-medium text-ui-black">{identity.name}</span>.
              </p>
              <div className="mt-8 flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleContinue}
                  className="inline-flex w-full items-center justify-center rounded-md bg-ui-gold-500 px-4 py-2.5 text-sm font-semibold text-ui-black transition hover:bg-ui-gold-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500"
                >
                  Continue
                </button>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="inline-flex w-full items-center justify-center rounded-md border border-gray-200 px-4 py-2.5 text-sm font-medium text-ui-black transition hover:border-ui-gold-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500"
                >
                  Sign out
                </button>
              </div>
            </>
          ) : (
            <>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ui-black">Sign in</h1>
              <p className="mt-3 text-sm text-ui-silver">
                Use your University of Idaho account to open the editor, SLC, and Event
                Services tools.
              </p>

              {message && (
                <div
                  role="alert"
                  className="mt-6 rounded-md border border-ui-gold-300 bg-ui-gold-50 px-4 py-3"
                >
                  <p className="text-sm font-semibold text-ui-black">{message.heading}</p>
                  <p className="mt-1 text-sm text-ui-silver">{message.body}</p>
                </div>
              )}

              <form onSubmit={handleSubmit} noValidate className="mt-8">
                <label htmlFor="login-email" className="block text-sm font-medium text-ui-black">
                  University email
                </label>
                <input
                  id="login-email"
                  name="email"
                  type="email"
                  autoComplete="username"
                  inputMode="email"
                  spellCheck={false}
                  placeholder={`you@${UI_DOMAIN}`}
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    setHint(null);
                  }}
                  className="mt-1.5 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-ui-black placeholder:text-gray-400 focus:border-ui-clearwater-500 focus:outline-none focus:ring-2 focus:ring-ui-clearwater-200"
                />
                <p className="mt-1.5 text-xs text-ui-silver">
                  Optional. Pre-fills the University sign-in page; you'll enter your password there.
                </p>
                {hint && (
                  <p className="mt-2 text-sm text-ui-silver" role="status">
                    {hint}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="mt-6 inline-flex w-full items-center justify-center gap-2.5 rounded-md bg-ui-gold-500 px-4 py-2.5 text-sm font-semibold text-ui-black transition hover:bg-ui-gold-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 disabled:cursor-wait disabled:opacity-70"
                >
                  <MicrosoftMark />
                  {submitting ? 'Redirecting to Microsoft…' : 'Continue with Microsoft'}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-ui-silver">
          Access is managed by University Communications &amp; Marketing.
        </p>
      </main>
    </div>
  );
}
