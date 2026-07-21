export interface EditableBodyLink {
  Url: string;
  Anchor_Text: string;
  Display_Order?: number;
}

const EMAIL_ADDRESS_PATTERN = /^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$/i;
const ANCHOR_PATTERN = /<a\s+href=["']([^"']+)["'][^>]*>([^<]+)<\/a>/gi;

export function normalizeEditableLinkUrl(value: string): string {
  const trimmed = value.trim();
  if (EMAIL_ADDRESS_PATTERN.test(trimmed)) return `mailto:${trimmed}`;
  return trimmed;
}

export function isSafeLinkDestination(value: string): boolean {
  const normalized = normalizeEditableLinkUrl(value);
  try {
    const parsed = new URL(normalized);
    if (parsed.protocol === 'https:') {
      return Boolean(parsed.hostname) && !parsed.username && !parsed.password;
    }
    if (parsed.protocol === 'mailto:') {
      return EMAIL_ADDRESS_PATTERN.test(parsed.pathname) && !parsed.search && !parsed.hash;
    }
  } catch {
    return false;
  }
  return false;
}

export function prepareBodyForEditing(
  body: string,
  storedLinks: Array<{ Url: string; Anchor_Text: string | null; Display_Order?: number }> = [],
): { body: string; links: EditableBodyLink[] } {
  const bodyLinks: EditableBodyLink[] = [];
  const plainBody = body.replace(ANCHOR_PATTERN, (_match, href: string, anchorText: string) => {
    if (isSafeLinkDestination(href)) {
      bodyLinks.push({
        Url: normalizeEditableLinkUrl(href),
        Anchor_Text: anchorText,
        Display_Order: bodyLinks.length,
      });
    }
    return anchorText;
  });

  const links = [...bodyLinks];
  for (const link of [...storedLinks].sort(
    (left, right) => (left.Display_Order ?? 0) - (right.Display_Order ?? 0),
  )) {
    const normalizedUrl = normalizeEditableLinkUrl(link.Url);
    const anchorText = link.Anchor_Text?.trim() || '';
    if (!isSafeLinkDestination(normalizedUrl)) continue;
    if (links.some(
      (candidate) => candidate.Url === normalizedUrl && candidate.Anchor_Text === anchorText,
    )) continue;
    links.push({
      Url: normalizedUrl,
      Anchor_Text: anchorText,
      Display_Order: links.length,
    });
  }

  return { body: plainBody, links: links.slice(0, 3) };
}

function linkLabel(link: EditableBodyLink): string {
  const explicitLabel = link.Anchor_Text.trim();
  if (explicitLabel) return explicitLabel.replace(/[<>]/g, '');
  const normalizedUrl = normalizeEditableLinkUrl(link.Url);
  return normalizedUrl.startsWith('mailto:')
    ? normalizedUrl.slice('mailto:'.length)
    : normalizedUrl;
}

function safeAttributeValue(value: string): string {
  return value.replace(/["'<>]/g, (character) => encodeURIComponent(character));
}

export function buildLinkedBody(body: string, links: EditableBodyLink[]): string {
  const validLinks = links
    .map((link, index) => ({
      ...link,
      Url: normalizeEditableLinkUrl(link.Url),
      Display_Order: index,
    }))
    .filter((link) => link.Url && isSafeLinkDestination(link.Url));

  const occupiedRanges: Array<{ start: number; end: number }> = [];
  const replacements: Array<{ start: number; end: number; markup: string }> = [];
  const appendedLinks: string[] = [];

  for (const link of validLinks) {
    const label = linkLabel(link);
    if (!label) continue;

    let matchIndex = body.indexOf(label);
    while (
      matchIndex >= 0
      && occupiedRanges.some(
        (range) => matchIndex < range.end && matchIndex + label.length > range.start,
      )
    ) {
      matchIndex = body.indexOf(label, matchIndex + label.length);
    }

    const markup = `<a href="${safeAttributeValue(link.Url)}">${label}</a>`;
    if (matchIndex >= 0) {
      occupiedRanges.push({ start: matchIndex, end: matchIndex + label.length });
      replacements.push({
        start: matchIndex,
        end: matchIndex + label.length,
        markup,
      });
    } else {
      appendedLinks.push(markup);
    }
  }

  let linkedBody = body;
  for (const replacement of replacements.sort((left, right) => right.start - left.start)) {
    linkedBody = `${linkedBody.slice(0, replacement.start)}${replacement.markup}${linkedBody.slice(replacement.end)}`;
  }

  return [linkedBody.trimEnd(), ...appendedLinks].filter(Boolean).join('\n');
}

export function normalizedBodyLinks(links: EditableBodyLink[]): EditableBodyLink[] {
  return links
    .map((link, index) => ({
      Url: normalizeEditableLinkUrl(link.Url),
      Anchor_Text: link.Anchor_Text.trim(),
      Display_Order: index,
    }))
    .filter((link) => link.Url && isSafeLinkDestination(link.Url));
}
