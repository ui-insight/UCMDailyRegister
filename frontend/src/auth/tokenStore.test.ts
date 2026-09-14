import { beforeEach, describe, expect, it } from 'vitest';
import { clearToken, getIdentity, getToken, setToken, subscribe } from './tokenStore';
import { getSubmitterRole, homeForRole, pathRequiresRole, roleMayOpen } from '../utils/submitterRole';

function fakeJwt(claims: Record<string, unknown>): string {
  const b64 = (obj: unknown) => btoa(JSON.stringify(obj))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(claims)}.signature`;
}

const future = Math.floor(Date.now() / 1000) + 3600;

describe('tokenStore', () => {
  beforeEach(() => {
    window.localStorage.clear();
    clearToken();
  });

  it('decodes a well-formed token into an identity', () => {
    setToken(fakeJwt({ sub: 'jdoe@uidaho.edu', name: 'J Doe', role: 'slc', exp: future }));
    expect(getIdentity()).toEqual({
      subject: 'jdoe@uidaho.edu',
      name: 'J Doe',
      role: 'slc',
      exp: future,
    });
    expect(window.localStorage.getItem('ucm_session_token')).not.toBeNull();
  });

  it('drops an expired token instead of storing it', () => {
    setToken(fakeJwt({ sub: 'x', name: 'x', role: 'staff', exp: future - 7200 }));
    expect(getToken()).toBeNull();
    expect(getIdentity()).toBeNull();
    expect(window.localStorage.getItem('ucm_session_token')).toBeNull();
  });

  it('refuses a token whose role is public', () => {
    setToken(fakeJwt({ sub: 'x', name: 'x', role: 'public', exp: future }));
    expect(getIdentity()).toBeNull();
  });

  it('refuses garbage', () => {
    setToken('not.a.jwt');
    expect(getIdentity()).toBeNull();
  });

  it('notifies subscribers on change', () => {
    let calls = 0;
    const unsubscribe = subscribe(() => {
      calls += 1;
    });
    setToken(fakeJwt({ sub: 'x', name: 'x', role: 'ops', exp: future }));
    clearToken();
    unsubscribe();
    clearToken();
    expect(calls).toBe(2);
  });
});

describe('getSubmitterRole with a session token', () => {
  beforeEach(() => {
    window.localStorage.clear();
    clearToken();
    window.history.replaceState(null, '', '/');
  });

  it('is public with no token and no stored role', () => {
    expect(getSubmitterRole()).toBe('public');
  });

  it('uses the token role, beating the URL heuristic', () => {
    window.history.replaceState(null, '', '/dashboard');
    setToken(fakeJwt({ sub: 'x', name: 'x', role: 'ops', exp: future }));
    expect(getSubmitterRole()).toBe('ops');
  });
});

describe('route helpers', () => {
  it('staff may open everything', () => {
    for (const path of ['/dashboard', '/slc-calendar', '/ops-triage', '/submit', '/edit/abc']) {
      expect(roleMayOpen('staff', path)).toBe(true);
    }
  });

  it('slc and ops are scoped to their own pages', () => {
    expect(roleMayOpen('slc', '/slc-calendar')).toBe(true);
    expect(roleMayOpen('slc', '/dashboard')).toBe(false);
    expect(roleMayOpen('slc', '/ops-triage')).toBe(false);
    expect(roleMayOpen('ops', '/ops-triage')).toBe(true);
    expect(roleMayOpen('ops', '/slc-triage')).toBe(false);
    expect(roleMayOpen('ops', '/submit')).toBe(true);
  });

  it('knows which paths need a role', () => {
    expect(pathRequiresRole('/submit')).toBe(false);
    expect(pathRequiresRole('/submit-slc-event')).toBe(true);
    expect(pathRequiresRole('/dashboard')).toBe(true);
    expect(pathRequiresRole('/ops-triage')).toBe(true);
    expect(pathRequiresRole('/')).toBe(false);
  });

  it('routes each role home', () => {
    expect(homeForRole('staff')).toBe('/dashboard');
    expect(homeForRole('slc')).toBe('/slc-calendar');
    expect(homeForRole('ops')).toBe('/ops-triage');
    expect(homeForRole('public')).toBe('/submit');
  });
});
