export type SubmitterRole = 'public' | 'staff' | 'slc';

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
const SLC_ROUTE_PREFIXES = ['/slc-calendar', '/submit-slc-event'];

function parseRole(value: string | null): SubmitterRole | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  if (normalized === 'staff') return 'staff';
  if (normalized === 'slc') return 'slc';
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

  return preferredRole;
}

export function getSubmitterRole(): SubmitterRole {
  if (typeof window === 'undefined') {
    return 'public';
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
