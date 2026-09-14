import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useIdentity, useSsoEnabled } from './useAuth';
import { pathRequiresRole, roleMayOpen } from '../utils/submitterRole';

/**
 * Route guard for the role-gated pages. Only active when the deployment
 * signs users in through SSO; under the trusted-header deployment the
 * browser has no way to know its role, so the pages render and the backend
 * answers 403 exactly as it does today.
 *
 * This is a UX guard, not a security boundary: every API call is still
 * checked server-side. Its job is to send an anonymous visitor to the
 * landing page (where they can sign in) instead of showing them an empty
 * dashboard full of 403s.
 */
export default function RequireRole() {
  const ssoEnabled = useSsoEnabled();
  const identity = useIdentity();
  const location = useLocation();

  if (ssoEnabled !== true || !pathRequiresRole(location.pathname)) {
    return <Outlet />;
  }

  if (!identity || !roleMayOpen(identity.role, location.pathname)) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
