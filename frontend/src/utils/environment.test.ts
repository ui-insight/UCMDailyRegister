import { describe, expect, it } from 'vitest';
import { resolveEnvironment } from './environment';

describe('environment identity outside deployed sites', () => {
  it.each(['localhost', '127.0.0.1', '::1', '[::1]'])('keeps %s visibly local despite a production build', host => {
    expect(resolveEnvironment(host, 'production')).toBe('local');
  });
  it('uses explicit configuration for a custom host and identifies missing configuration', () => {
    expect(resolveEnvironment('preview.example.org', 'development')).toBe('development');
    expect(resolveEnvironment('preview.example.org')).toBe('unknown');
  });
});
