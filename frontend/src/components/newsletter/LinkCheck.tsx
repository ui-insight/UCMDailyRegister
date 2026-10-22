import type { LinkFinding } from '../../types/newsletter';
import { listBodyLinks } from '../../utils/bodyLinks';

interface LinkCheckProps {
  body: string;
  findings: LinkFinding[];
}

function displayDestination(href: string): string {
  if (href.startsWith('mailto:')) return href.slice('mailto:'.length);
  try {
    const url = new URL(href);
    return `${url.hostname}${url.pathname === '/' ? '' : url.pathname}`;
  } catch {
    return href;
  }
}

function findingMessage(finding: LinkFinding): string {
  const words = finding.Text ? `"${finding.Text}"` : 'A link';
  switch (finding.Kind) {
    case 'unsafe_link':
      return `${words} won't be clickable in Word: ${finding.Href} isn't a secure web or email address.`;
    case 'tracking_link':
      return `${words} goes through an email security wrapper. Real address: ${finding.Suggested_Href}`;
    case 'bare_url':
      return `Web address written out as text: ${finding.Href}. Link descriptive words instead.`;
    case 'missing_submitted_link':
      return `A submitted link isn't in this copy: ${finding.Href}`;
  }
}

/**
 * The links an item will carry into the Word export, each openable so staff
 * can test it, plus any problems the backend found before export.
 */
export default function LinkCheck({ body, findings }: LinkCheckProps) {
  const links = listBodyLinks(body).filter((link) => link.safe);
  if (links.length === 0 && findings.length === 0) return null;

  return (
    <div className="mt-2 space-y-1 text-[11px] leading-4">
      {links.length > 0 && (
        <ul aria-label="Links in this item" className="space-y-0.5 text-gray-500">
          {links.map((link, index) => (
            <li key={`${link.href}-${index}`} className="break-words">
              <span className="text-gray-700">{link.text}</span>
              {' → '}
              <a
                href={link.href}
                target={link.href.startsWith('mailto:') ? undefined : '_blank'}
                rel="noopener noreferrer"
                className="text-ui-clearwater-700 underline decoration-ui-clearwater-300 underline-offset-2"
              >
                {displayDestination(link.href)}
              </a>
            </li>
          ))}
        </ul>
      )}
      {findings.length > 0 && (
        <ul aria-label="Link problems" className="space-y-0.5">
          {findings.map((finding, index) => (
            <li key={`${finding.Kind}-${index}`} className="break-words text-status-warning-800">
              ⚠ {findingMessage(finding)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
