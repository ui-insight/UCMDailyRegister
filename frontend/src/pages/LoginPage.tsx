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

function MailIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="h-4 w-4"
    >
      <rect x="2.5" y="4.5" width="15" height="11" rx="2" />
      <path d="m3 6 7 5 7-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="mt-0.5 h-3.5 w-3.5 shrink-0"
    >
      <rect x="4" y="8.5" width="12" height="9" rx="1.5" />
      <path d="M7 8.5V6a3 3 0 0 1 6 0v2.5" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="h-3.5 w-3.5"
    >
      <path d="m5 10.5 3.2 3.2L15 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const WORKSPACES = [
  { name: 'Editor tools', detail: 'Dashboard, builder, style rules, scheduling' },
  { name: 'SLC Leadership', detail: 'Strategic and signature events calendar' },
  { name: 'Event Services', detail: 'Operational triage for upcoming events' },
];

const PRIMARY_BUTTON =
  'inline-flex w-full items-center justify-center gap-2.5 rounded-lg bg-ui-gold-500 px-4 py-3 '
  + 'text-sm font-semibold text-ui-black shadow-sm transition hover:bg-ui-gold-400 hover:shadow '
  + 'focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 '
  + 'focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-70';

const SECONDARY_BUTTON =
  'inline-flex w-full items-center justify-center rounded-lg border border-gray-300 bg-white '
  + 'px-4 py-3 text-sm font-medium text-ui-black transition hover:border-gray-400 hover:bg-gray-50 '
  + 'focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 '
  + 'focus-visible:ring-offset-2';

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
    <div className="flex min-h-screen flex-col bg-white lg:flex-row">
      {/* Brand panel: full height on desktop, a compact header on phones. */}
      <aside className="relative overflow-hidden bg-gray-900 text-white lg:flex lg:w-[46%] lg:max-w-xl lg:flex-col lg:justify-between">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_rgba(241,179,0,0.18),_transparent_55%)]"
        />
        <div aria-hidden="true" className="absolute inset-x-0 top-0 h-1 bg-ui-gold-500" />

        <div className="relative px-6 py-5 lg:px-12 lg:pt-12">
          <img
            src="/ui-logo-gold-white-horizontal.png"
            alt="University of Idaho"
            className="h-8 w-auto lg:h-10"
          />
        </div>

        <div className="relative hidden px-12 pb-12 lg:block">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ui-gold-400">
            UCM Newsletter Builder
          </p>
          <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-tight">
            The Daily Register and My UI, produced in one place.
          </h2>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-gray-300">
            Sign in with your University account to reach the workspace your role grants.
            Campus submitters don't need an account; they use the public submission form.
          </p>
          <ul className="mt-10 space-y-4">
            {WORKSPACES.map((workspace) => (
              <li key={workspace.name} className="flex gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ui-gold-500/15 text-ui-gold-400 ring-1 ring-inset ring-ui-gold-500/40">
                  <CheckIcon />
                </span>
                <div>
                  <p className="text-sm font-medium text-white">{workspace.name}</p>
                  <p className="text-xs text-gray-400">{workspace.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative hidden px-12 pb-10 text-xs text-gray-500 lg:block">
          University Communications &amp; Marketing
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex flex-1 items-start justify-center px-6 py-10 lg:items-center lg:px-16 lg:py-12">
        <div className="w-full max-w-sm">
          {identity ? (
            <>
              <h1 className="text-3xl font-semibold tracking-tight text-ui-black">
                You're signed in
              </h1>
              <p className="mt-3 text-sm text-ui-silver">
                Signed in as <span className="font-medium text-ui-black">{identity.name}</span>.
              </p>
              <div className="mt-8 flex flex-col gap-3">
                <button type="button" onClick={handleContinue} className={PRIMARY_BUTTON}>
                  Continue
                </button>
                <button type="button" onClick={handleSignOut} className={SECONDARY_BUTTON}>
                  Sign out
                </button>
              </div>
            </>
          ) : (
            <>
              <h1 className="text-3xl font-semibold tracking-tight text-ui-black">Sign in</h1>
              <p className="mt-3 text-sm leading-relaxed text-ui-silver">
                Use your University of Idaho account. You'll be taken to the University
                sign-in page to finish.
              </p>

              {message && (
                <div
                  role="alert"
                  className="mt-6 flex gap-3 rounded-lg border border-ui-gold-300 bg-ui-gold-50 px-4 py-3.5"
                >
                  <span
                    aria-hidden="true"
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ui-gold-500 text-[11px] font-bold text-ui-black"
                  >
                    !
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-ui-black">{message.heading}</p>
                    <p className="mt-1 text-sm leading-relaxed text-gray-600">{message.body}</p>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} noValidate className="mt-8">
                <label htmlFor="login-email" className="block text-sm font-medium text-ui-black">
                  University email
                  <span className="ml-1.5 text-xs font-normal text-ui-silver">(optional)</span>
                </label>
                <div className="relative mt-2">
                  <span className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-gray-400">
                    <MailIcon />
                  </span>
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
                    className="block w-full rounded-lg border border-gray-300 bg-white py-3 pl-10 pr-3.5 text-sm text-ui-black shadow-sm placeholder:text-gray-400 focus:border-ui-clearwater-500 focus:outline-none focus:ring-2 focus:ring-ui-clearwater-200"
                  />
                </div>
                {hint ? (
                  <p className="mt-2 text-sm text-gray-600" role="status">
                    {hint}
                  </p>
                ) : (
                  <p className="mt-2 text-xs text-ui-silver">
                    Pre-fills the University sign-in page so you can skip the account picker.
                  </p>
                )}

                <button type="submit" disabled={submitting} className={`mt-6 ${PRIMARY_BUTTON}`}>
                  <MicrosoftMark />
                  {submitting ? 'Redirecting to Microsoft…' : 'Continue with Microsoft'}
                </button>
              </form>

              <p className="mt-6 flex items-start gap-2 text-xs leading-relaxed text-ui-silver">
                <LockIcon />
                <span>
                  Your password is entered on the University sign-in page, never here. This app
                  only learns who you are and which groups you belong to.
                </span>
              </p>
            </>
          )}

          <p className="mt-10 border-t border-gray-100 pt-6 text-xs text-ui-silver">
            Access is managed by University Communications &amp; Marketing. If you need access,
            contact UCM.
          </p>
        </div>
      </main>
    </div>
  );
}
