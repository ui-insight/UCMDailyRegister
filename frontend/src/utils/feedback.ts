import type { SubmitterRole } from './submitterRole';

export interface FeedbackContext {
  Submitter_Role: SubmitterRole;
  Route: string;
  App_Environment: string;
  Host: string;
  Browser: string;
  Viewport: string;
}

export function getBrowserFeedbackContext(
  role: SubmitterRole,
  route: string,
): FeedbackContext {
  const appEnvironment = import.meta.env.VITE_APP_ENV || import.meta.env.MODE || 'unknown';

  if (typeof window === 'undefined') {
    return {
      Submitter_Role: role,
      Route: route,
      App_Environment: appEnvironment,
      Host: 'unknown',
      Browser: 'unknown',
      Viewport: 'unknown',
    };
  }

  return {
    Submitter_Role: role,
    Route: route,
    App_Environment: appEnvironment,
    Host: window.location.host || 'unknown',
    Browser: window.navigator.userAgent,
    Viewport: `${window.innerWidth}x${window.innerHeight}`,
  };
}

export function buildGitHubIssueUrl(title: string, body: string): string {
  const url = new URL('https://github.com/ui-insight/UCMDailyRegister/issues/new');
  url.searchParams.set('title', title);
  url.searchParams.set('body', body);
  return url.toString();
}
