/** Mirrors `app/schemas/auth.py`. */

export interface AuthConfig {
  sso_enabled: boolean;
}

export interface CurrentUser {
  subject: string;
  name: string;
  role: 'staff' | 'slc' | 'ops';
}
