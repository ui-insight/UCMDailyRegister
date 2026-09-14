import { getIdentity } from '../auth/tokenStore';

export type SubmitterRole = 'public' | 'staff' | 'slc' | 'ops';

const STORAGE_KEY = 'ucm_submitter_role';
const STAFF_ONLY_ROUTE_PREFIXES = [
  '/dashboard',
  '/builder',
  '/recurring-messages',
  '/style-rules',
  '/settings',
  '/edit',
  '/home',
];
const SLC_ROUTE_PREFIXES = ['/slc-calendar', '/slc-triage', '/submit-slc-event'];
const OPS_ROUTE_PREFIXES = ['/ops-triage'];

function parseRole(value: string | null): SubmitterRole | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  if (normalized === 'staff') return 'staff';
  if (normalized === 'slc') return 'slc';
  if (normalized === 'ops') return 'ops';
  if (normalized === 'public') return 'public';
  return null;
}

function matchesRoutePrefix(pathname: string, prefix: string): boolean {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

function inferRoleFromPath(
  pathname: string,
  preferredRole: SubmitterRole | null,
): SubmitterRole | null {
  const normalizedPath = pathname.toLowerCase();

  if (STAFF_ONLY_ROUTE_PREFIXES.some((prefix) => matchesRoutePrefix(normalizedPath, prefix))) {
    return 'staff';
  }

  if (SLC_ROUTE_PREFIXES.some((prefix) => matchesRoutePrefix(normalizedPath, prefix))) {
    return preferredRole === 'staff' || preferredRole === 'slc' ? preferredRole : 'slc';
  }

  if (OPS_ROUTE_PREFIXES.some((prefix) => matchesRoutePrefix(normalizedPath, prefix))) {
    return preferredRole === 'staff' || preferredRole === 'ops' ? preferredRole : 'ops';
  }

  return preferredRole;
}

/** Route prefixes each role may open. `staff` passes every gate, matching
 * `require_staff_or_*` on the backend. */
export function roleMayOpen(role: SubmitterRole, pathname: string): boolean {
  const normalizedPath = pathname.toLowerCase();
  if (role === 'staff') return true;
  if (STAFF_ONLY_ROUTE_PREFIXES.some((prefix) => matchesRoutePrefix(normalizedPath, prefix))) {
    return false;
  }
  if (SLC_ROUTE_PREFIXES.some((prefix) => matchesRoutePrefix(normalizedPath, prefix))) {
    return role === 'slc';
  }
  if (OPS_ROUTE_PREFIXES.some((prefix) => matchesRoutePrefix(normalizedPath, prefix))) {
    return role === 'ops';
  }
  return true;
}

/** Whether a path needs a signed-in role at all (vs. open to submitters). */
export function pathRequiresRole(pathname: string): boolean {
  const normalizedPath = pathname.toLowerCase();
  return [...STAFF_ONLY_ROUTE_PREFIXES, ...SLC_ROUTE_PREFIXES, ...OPS_ROUTE_PREFIXES]
    .some((prefix) => matchesRoutePrefix(normalizedPath, prefix));
}

/** Where a signed-in role lands after sign-in. */
export function homeForRole(role: SubmitterRole): string {
  switch (role) {
    case 'staff':
      return '/dashboard';
    case 'slc':
      return '/slc-calendar';
    case 'ops':
      return '/ops-triage';
    default:
      return '/submit';
  }
}

export function getSubmitterRole(): SubmitterRole {
  if (typeof window === 'undefined') {
    return 'public';
  }

  // A signed-in identity is authoritative: the backend verified it. The
  // URL/localStorage heuristic below only exists for the trusted-header
  // deployment, where the browser never learns its role any other way.
  const identity = getIdentity();
  if (identity) {
    return identity.role;
  }

  const queryRole = parseRole(new URLSearchParams(window.location.search).get('role'));
  const storedRole = parseRole(window.localStorage.getItem(STORAGE_KEY));
  const resolvedRole = inferRoleFromPath(window.location.pathname, queryRole ?? storedRole);

  if (resolvedRole && resolvedRole !== storedRole) {
    window.localStorage.setItem(STORAGE_KEY, resolvedRole);
  }

  return resolvedRole ?? 'public';
}

export function setSubmitterRole(role: SubmitterRole) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, role);
}

export function getSubmitterRoleHeaders(): HeadersInit {
  return {};
}
