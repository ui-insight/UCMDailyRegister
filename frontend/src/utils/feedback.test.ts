import { describe, expect, it } from 'vitest';
import { buildGitHubIssueUrl } from './feedback';

describe('feedback helpers', () => {
  it('builds a GitHub issue URL for staff export only', () => {
    const href = buildGitHubIssueUrl('Bug: Filter resets', '## User Report\n\nIt reset.');
    const url = new URL(href);

    expect(url.hostname).toBe('github.com');
    expect(url.pathname).toBe('/ui-insight/UCMDailyRegister/issues/new');
    expect(url.searchParams.get('title')).toBe('Bug: Filter resets');
    expect(url.searchParams.get('body')).toContain('It reset.');
  });
});
