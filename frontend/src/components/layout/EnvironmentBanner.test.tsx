import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import EnvironmentBanner from './EnvironmentBanner';
import { getBrowserFeedbackContext } from '../../utils/feedback';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('site identity and feedback provenance', () => {
  it.each([
    ['ucmnews-dev.insight.uidaho.edu', 'production', 'development', 'DEV'],
    ['ucmnews.insight.uidaho.edu', 'development', 'production', 'PROD'],
  ])('identifies %s from its address even with a conflicting build setting', (host, build, expected, prefix) => {
    vi.stubEnv('VITE_APP_ENV', build);
    vi.stubGlobal('window', { location: { host, hostname: host }, navigator: { userAgent: 'Synthetic browser' }, innerWidth: 1024, innerHeight: 768 });
    render(<EnvironmentBanner />);
    expect(screen.getByRole('complementary', { name: 'Site environment' })).toHaveTextContent(new RegExp(expected, 'i'));
    expect(document.title).toBe(`[${prefix}] UCM Daily Register`);
    expect(getBrowserFeedbackContext('staff', '/builder')).toMatchObject({ Host: host, App_Environment: expected });
    if (expected === 'development') {
      expect(screen.getByRole('link', { name: 'Open production' })).toHaveAttribute('href', 'https://ucmnews.insight.uidaho.edu');
      expect(screen.getByText('Work here is separate from production.')).toBeVisible();
    } else {
      expect(screen.queryByRole('link', { name: 'Open production' })).not.toBeInTheDocument();
    }
  });
});
