/**
 * The SLC and Event Services tools hidden from UCM News.
 *
 * Their pages, API, and data are still in place while their owners decide
 * whether they move to a separate application; only the routes change, so
 * old bookmarks and the sign-in home for the `slc` and `ops` roles land on
 * RetiredToolPage instead of a 404.
 */
const RETIRED_TOOLS: { name: string; paths: string[] }[] = [
  {
    name: 'The SLC events calendar',
    paths: ['/slc-calendar', '/slc-triage', '/slc-digest', '/submit-slc-event'],
  },
  {
    name: 'Event Services triage',
    paths: ['/ops-triage'],
  },
];

export const RETIRED_TOOL_PATHS = RETIRED_TOOLS.flatMap((tool) => tool.paths);

export function retiredToolNameFor(pathname: string): string {
  const normalized = pathname.toLowerCase().replace(/\/+$/, '');
  return RETIRED_TOOLS.find((tool) => tool.paths.includes(normalized))?.name
    ?? 'This tool';
}
