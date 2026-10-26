export const PRODUCTION_URL = 'https://ucmnews.insight.uidaho.edu';

export type AppEnvironment = 'production' | 'development' | 'local' | 'unknown';

// A Docker production build also runs on dev. The site address is authoritative.
export function resolveEnvironment(hostname: string, configured = ''): AppEnvironment {
  const host = hostname.toLowerCase();
  if (host === 'ucmnews.insight.uidaho.edu') return 'production';
  if (host === 'ucmnews-dev.insight.uidaho.edu') return 'development';
  if (['localhost', '127.0.0.1', '[::1]', '::1'].includes(host)) return 'local';
  if (configured === 'production' || configured === 'development') return configured;
  return 'unknown';
}

export function getBrowserEnvironment(): AppEnvironment {
  return resolveEnvironment(
    typeof window === 'undefined' ? '' : window.location.hostname,
    import.meta.env.VITE_APP_ENV,
  );
}
