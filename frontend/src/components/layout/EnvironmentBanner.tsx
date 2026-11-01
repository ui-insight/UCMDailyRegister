import { useEffect } from 'react';
import { getBrowserEnvironment, PRODUCTION_URL } from '../../utils/environment';

export default function EnvironmentBanner() {
  const environment = getBrowserEnvironment();
  const production = environment === 'production';
  const label = { production: 'Production', development: 'Development', local: 'Local development', unknown: 'Unidentified environment' }[environment];

  useEffect(() => {
    const prefix = { production: 'PROD', development: 'DEV', local: 'LOCAL', unknown: 'UNKNOWN' }[environment];
    document.title = `[${prefix}] UCM Daily Register`;
  }, [environment]);

  return (
    <aside
      aria-label="Site environment"
      className={`sticky top-0 z-30 flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-2 text-sm ${production ? 'bg-ui-clearwater-900 text-ui-clearwater-50' : 'bg-ui-gold-200 text-ui-gold-900'}`}
    >
      <strong className="uppercase tracking-wide">{label}</strong>
      <span>{production ? 'Live newsletters and submissions.' : 'Work here is separate from production.'}</span>
      {!production && (
        <a className="font-semibold underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-4" href={PRODUCTION_URL}>
          Open production
        </a>
      )}
      <span className="ml-auto break-all text-xs">{window.location.host}</span>
    </aside>
  );
}
