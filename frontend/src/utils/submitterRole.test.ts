import { describe, expect, it } from 'vitest';
import { pathRequiresRole, roleMayOpen } from './submitterRole';

const STAFF_PAGES = [
  '/dashboard',
  '/builder',
  '/edit/abc',
  '/recurring-messages',
  '/style-rules',
  '/feedback',
  '/data-governance',
  '/settings',
];

describe('staff-only routes', () => {
  it.each(STAFF_PAGES)('%s is closed to a signed-in submitter', (path) => {
    expect(pathRequiresRole(path)).toBe(true);
    expect(roleMayOpen('submitter', path)).toBe(false);
    expect(roleMayOpen('public', path)).toBe(false);
  });

  it.each(STAFF_PAGES)('%s is open to staff', (path) => {
    expect(roleMayOpen('staff', path)).toBe(true);
  });

  it('leaves the submission form open to submitters', () => {
    expect(pathRequiresRole('/submit')).toBe(false);
    expect(roleMayOpen('submitter', '/submit')).toBe(true);
  });
});
