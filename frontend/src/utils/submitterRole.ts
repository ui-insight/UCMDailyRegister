export type SubmitterRole = 'public' | 'staff';

const STORAGE_KEY = 'ucm_submitter_role';

function parseRole(value: string | null): SubmitterRole | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  return normalized === 'staff' ? 'staff' : normalized === 'public' ? 'public' : null;
}

export function getSubmitterRole(): SubmitterRole {
  if (typeof window === 'undefined') {
    return 'public';
  }

  const queryRole = parseRole(new URLSearchParams(window.location.search).get('role'));
  if (queryRole) {
    window.localStorage.setItem(STORAGE_KEY, queryRole);
    return queryRole;
  }

  return parseRole(window.localStorage.getItem(STORAGE_KEY)) ?? 'public';
}

export function setSubmitterRole(role: SubmitterRole) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, role);
}

export function getSubmitterRoleHeaders(): HeadersInit {
  const role = getSubmitterRole();
  return role === 'staff' ? { 'X-User-Role': role } : {};
}
