import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useIdentity, useSsoEnabled } from './useAuth';
import { roleMayOpen } from '../utils/submitterRole';
import { loginUrlFor } from './loginUrl';

/**
 * Route guard for the role-gated pages. Only active when the deployment
 * signs users in through SSO; under the trusted-header deployment the
 * browser has no way to know its role, so the pages render and the backend
 * answers 403 exactly as it does today.
 *
 * Under SSO every page behind this guard needs a signed-in user, submitters
 * included (ADR-002); staff-only pages also need the staff role.
 *
 * This is a UX guard, not a security boundary: every API call is still
 * checked server-side. Its job is to send an anonymous visitor to sign in
 * instead of showing them a form that cannot be sent or a dashboard full
 * of 403s.
 */
export default function RequireRole() {
  const ssoEnabled = useSsoEnabled();
  const identity = useIdentity();
  const location = useLocation();

  if (ssoEnabled !== true) {
    return <Outlet />;
  }

  if (!identity || !roleMayOpen(identity.role, location.pathname)) {
    return <Navigate to={loginUrlFor(location.pathname)} replace />;
  }

  return <Outlet />;
}
