import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getIdentity, setToken } from '../auth/tokenStore';
import { homeForRole, setSubmitterRole } from '../utils/submitterRole';

/** Where the backend sends the browser after Entra returns. Must match
 * `OIDC_POST_LOGIN_REDIRECT` on the server. */
export const SSO_CALLBACK_PATH = '/sso/callback';

interface CallbackResult {
  accessToken: string | null;
  /** Reason code from the backend; see `ERROR_*` in `app/api/v1/sso.py`. */
  error: string | null;
}

/** Both the token and a refusal ride the URL fragment, which is never sent to
 * a server, so neither lands in access logs, history, or the Referer. */
function readCallbackResult(): CallbackResult {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  return {
    accessToken: params.get('access_token'),
    error: params.get('error'),
  };
}

interface CallbackMessage {
  heading: string;
  body: string;
}

const FALLBACK: CallbackMessage = {
  heading: "Sign-in didn't complete",
  body: 'Something went wrong on the way back from the University sign-in page. Please try again.',
};

/** One message per reason, phrased as what the reader should do next.
 * `not_authorized` matters most: until OIT assigns roles it is what everyone
 * sees, and it must read as "you're not set up yet", not "the app is broken". */
const MESSAGES: Record<string, CallbackMessage> = {
  not_authorized: {
    heading: "You're not set up for this app yet",
    body:
      'Your University sign-in worked, but your account has not been given access to '
      + 'the newsletter tools. Ask UCM to have you added, then try again. You can still '
      + 'submit items without signing in.',
  },
  unavailable: {
    heading: 'Sign-in is temporarily unavailable',
    body:
      "We couldn't confirm your access with the University directory. This is usually "
      + 'brief. Please try again in a few minutes.',
  },
  misconfigured: {
    heading: "Sign-in isn't set up correctly",
    body:
      "The app couldn't check your access because it has not been granted permission "
      + "to read University directory groups. Retrying won't help; this needs an "
      + 'administrator.',
  },
  no_account: {
    heading: "We couldn't read your University account",
    body: 'Sign-in did not return an email address for your account. Please contact UCM.',
  },
  sign_in_failed: FALLBACK,
};

/**
 * Completes single sign-on. The backend has already verified the Entra
 * response and minted this app's session token; this page takes it out of
 * the URL fragment, stores it, and sends the user to their role's home.
 *
 * It also renders every *failed* sign-in, because the backend redirects here
 * with a reason code rather than raising.
 */
export default function SsoCallbackPage() {
  const navigate = useNavigate();
  // Read once at first render: the effect below wipes the fragment.
  const [{ accessToken, error }] = useState(readCallbackResult);

  useEffect(() => {
    if (!accessToken) return;
    // Wipe it from the address bar before it can be copied or shared.
    window.history.replaceState(null, '', SSO_CALLBACK_PATH);
    setToken(accessToken);
    const identity = getIdentity();
    if (!identity) {
      // Token was malformed or already expired; the store dropped it.
      navigate('/', { replace: true });
      return;
    }
    setSubmitterRole(identity.role);
    navigate(homeForRole(identity.role), { replace: true });
  }, [accessToken, navigate]);

  if (accessToken) {
    return (
      <div className="min-h-screen bg-white">
        <main className="mx-auto max-w-xl px-6 py-16">
          <p className="text-sm text-ui-silver">Signing you in&hellip;</p>
        </main>
      </div>
    );
  }

  // Own keys only: `#error=constructor` would otherwise read an inherited
  // property off the plain-object table.
  const known = error !== null && Object.prototype.hasOwnProperty.call(MESSAGES, error)
    ? MESSAGES[error]
    : undefined;
  const { heading, body } = known ?? FALLBACK;

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
      <main className="mx-auto max-w-xl px-6 py-16">
        <p className="text-sm text-ui-silver">UCM Newsletter Builder</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ui-black">{heading}</h1>
        <p className="mt-3 text-sm text-ui-silver">{body}</p>
        <button
          type="button"
          onClick={() => navigate('/', { replace: true })}
          className="mt-8 inline-flex items-center rounded-md bg-ui-gold-500 px-4 py-2 text-sm font-semibold text-ui-black transition hover:bg-ui-gold-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500"
        >
          Back to start
        </button>
      </main>
    </div>
  );
}
