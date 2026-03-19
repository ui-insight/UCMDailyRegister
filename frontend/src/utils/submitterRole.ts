export type SubmitterRole = 'public' | 'staff';

export function getSubmitterRole(): SubmitterRole {
  if (typeof window === 'undefined') {
    return 'public';
  }

  const role = new URLSearchParams(window.location.search).get('role')?.toLowerCase();
  return role === 'staff' ? 'staff' : 'public';
}

export function getSubmitterRoleHeaders(): HeadersInit {
  const role = getSubmitterRole();
  return role === 'staff' ? { 'X-User-Role': role } : {};
}
