import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getIdentity, setToken } from '../auth/tokenStore';
import { homeForRole, roleMayOpen, setSubmitterRole } from '../utils/submitterRole';
import { loginUrlFor } from '../auth/loginUrl';

/** Where the backend sends the browser after Entra returns. Must match
 * `OIDC_POST_LOGIN_REDIRECT` on the server. */
export const SSO_CALLBACK_PATH = '/sso/callback';

interface CallbackResult {
  accessToken: string | null;
  /** Reason code from the backend; see `ERROR_*` in `app/api/v1/sso.py`. */
  error: string | null;
  /** In-app path the user was heading for, carried through the backend. */
  next: string | null;
}

/** Both the token and a refusal ride the URL fragment, which is never sent to
 * a server, so neither lands in access logs, history, or the Referer. */
function readCallbackResult(): CallbackResult {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const next = params.get('next');
  return {
    accessToken: params.get('access_token'),
    error: params.get('error'),
    next: next && next.startsWith('/') && !next.startsWith('//') ? next : null,
  };
}

/**
 * Completes single sign-on. The backend has already verified the Entra
 * response and minted this app's session token; this page takes it out of
 * the URL fragment, stores it, and sends the user to their role's home.
 *
 * A *failed* sign-in also arrives here, as a reason code; it is handed to the
 * login page, which explains it above the form so the user can retry.
 */
export default function SsoCallbackPage() {
  const navigate = useNavigate();
  // Read once at first render: the effect below wipes the fragment.
  const [{ accessToken, error, next }] = useState(readCallbackResult);

  useEffect(() => {
    // Wipe the fragment from the address bar before it can be copied or shared.
    window.history.replaceState(null, '', SSO_CALLBACK_PATH);
    if (!accessToken) {
      const params = new URLSearchParams({ error: error ?? 'sign_in_failed' });
      if (next) params.set('next', next);
      navigate(`${loginUrlFor(null)}?${params.toString()}`, { replace: true });
      return;
    }
    setToken(accessToken);
    const identity = getIdentity();
    if (!identity) {
      // Token was malformed or already expired; the store dropped it.
      navigate(loginUrlFor(next), { replace: true });
      return;
    }
    setSubmitterRole(identity.role);
    const target = next && roleMayOpen(identity.role, next) ? next : homeForRole(identity.role);
    navigate(target, { replace: true });
  }, [accessToken, error, next, navigate]);

  return (
    <div className="min-h-screen bg-white">
      <main className="mx-auto max-w-xl px-6 py-16">
        <p className="text-sm text-ui-silver">Signing you in&hellip;</p>
      </main>
    </div>
  );
}
