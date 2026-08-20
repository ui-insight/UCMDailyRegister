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

function canonicalLinkDestination(value: string): string {
  const normalized = normalizeEditableLinkUrl(value);
  try {
    return new URL(normalized).href;
  } catch {
    return normalized;
  }
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
  const standaloneAnchorLabels = new Set<string>();
  let plainBody = body.replace(ANCHOR_PATTERN, (
    match,
    href: string,
    anchorText: string,
    offset: number,
    source: string,
  ) => {
    if (isSafeLinkDestination(href)) {
      const normalizedUrl = normalizeEditableLinkUrl(href);
      const canonicalUrl = canonicalLinkDestination(normalizedUrl);
      if (!bodyLinks.some(
        (candidate) => canonicalLinkDestination(candidate.Url) === canonicalUrl,
      )) {
        bodyLinks.push({
          Url: normalizedUrl,
          Anchor_Text: anchorText,
          Display_Order: bodyLinks.length,
        });
      }

      const lineStart = source.lastIndexOf('\n', Math.max(0, offset - 1)) + 1;
      const nextLineBreak = source.indexOf('\n', offset + match.length);
      const lineEnd = nextLineBreak === -1 ? source.length : nextLineBreak;
      if (
        source.slice(lineStart, offset).trim() === ''
        && source.slice(offset + match.length, lineEnd).trim() === ''
      ) {
        standaloneAnchorLabels.add(anchorText.trim().toLocaleLowerCase());
      }
    }
    return anchorText;
  });

  // Older editor builds silently appended unmatched anchors at the end of the
  // body. Remove that trailing generated block when real prose precedes it.
  // The link metadata remains available in the link fields so an editor can
  // deliberately attach it to wording that actually exists in the body.
  const bodyLines = plainBody.split('\n');
  let trailingBlockStart = bodyLines.length;
  let foundStandaloneAnchor = false;
  for (let index = bodyLines.length - 1; index >= 0; index -= 1) {
    const label = bodyLines[index].trim().toLocaleLowerCase();
    if (!label) {
      trailingBlockStart = index;
      continue;
    }
    if (standaloneAnchorLabels.has(label)) {
      foundStandaloneAnchor = true;
      trailingBlockStart = index;
      continue;
    }
    break;
  }
  const hasEarlierProse = bodyLines
    .slice(0, trailingBlockStart)
    .some((line) => line.trim());
  if (foundStandaloneAnchor && hasEarlierProse) {
    plainBody = bodyLines.slice(0, trailingBlockStart).join('\n').trimEnd();
  } else {
    plainBody = plainBody.trimEnd();
  }

  const links = [...bodyLinks];
  for (const link of [...storedLinks].sort(
    (left, right) => (left.Display_Order ?? 0) - (right.Display_Order ?? 0),
  )) {
    const normalizedUrl = normalizeEditableLinkUrl(link.Url);
    const canonicalUrl = canonicalLinkDestination(normalizedUrl);
    const anchorText = link.Anchor_Text?.trim() || '';
    if (!isSafeLinkDestination(normalizedUrl)) continue;
    if (links.some(
      (candidate) => canonicalLinkDestination(candidate.Url) === canonicalUrl,
    )) continue;
    const matchingAnchorIndex = anchorText
      ? links.findIndex(
        (candidate) => (
          candidate.Anchor_Text.trim().toLocaleLowerCase()
          === anchorText.toLocaleLowerCase()
        ),
      )
      : -1;
    if (matchingAnchorIndex >= 0) {
      links[matchingAnchorIndex] = {
        ...links[matchingAnchorIndex],
        Url: normalizedUrl,
      };
      continue;
    }
    links.push({
      Url: normalizedUrl,
      Anchor_Text: anchorText,
      Display_Order: links.length,
    });
  }

  return { body: plainBody, links: links.slice(0, 3) };
}

export function synchronizeBodyWithLinkLabel(
  body: string,
  previousLabel: string,
  nextLabel: string,
): string {
  const previous = previousLabel.trim();
  const next = nextLabel.trim().replace(/[<>]/g, '');
  if (!next || previous === next) return body;
  if (!previous) {
    if (body.toLocaleLowerCase().includes(next.toLocaleLowerCase())) return body;
    return [body.trimEnd(), next].filter(Boolean).join('\n');
  }

  const matchIndex = body.toLocaleLowerCase().indexOf(previous.toLocaleLowerCase());
  if (matchIndex < 0) {
    if (body.toLocaleLowerCase().includes(next.toLocaleLowerCase())) return body;
    return [body.trimEnd(), next].filter(Boolean).join('\n');
  }

  return `${body.slice(0, matchIndex)}${next}${body.slice(matchIndex + previous.length)}`;
}

export function synchronizeLinksWithBodyChange(
  previousBody: string,
  nextBody: string,
  links: EditableBodyLink[],
): EditableBodyLink[] {
  return links.map((link) => {
    const label = link.Anchor_Text.trim();
    if (!label) return link;

    const labelIndex = previousBody.toLocaleLowerCase().indexOf(label.toLocaleLowerCase());
    if (labelIndex < 0) return link;

    const before = previousBody.slice(0, labelIndex);
    const after = previousBody.slice(labelIndex + label.length);
    if (!nextBody.startsWith(before) || !nextBody.endsWith(after)) return link;

    const replacementEnd = nextBody.length - after.length;
    const replacement = nextBody.slice(before.length, replacementEnd).trim().replace(/[<>]/g, '');
    if (!replacement || replacement === label) return link;
    return { ...link, Anchor_Text: replacement };
  });
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
  const seenDestinations = new Set<string>();
  const validLinks = links
    .map((link, index) => ({
      ...link,
      Url: normalizeEditableLinkUrl(link.Url),
      Display_Order: index,
    }))
    .filter((link) => {
      if (!link.Url || !isSafeLinkDestination(link.Url)) return false;
      const canonicalUrl = canonicalLinkDestination(link.Url);
      if (seenDestinations.has(canonicalUrl)) return false;
      seenDestinations.add(canonicalUrl);
      return true;
    });

  const occupiedRanges: Array<{ start: number; end: number }> = [];
  const replacements: Array<{ start: number; end: number; markup: string }> = [];
  for (const link of validLinks) {
    const label = linkLabel(link);
    if (!label) continue;

    const searchableBody = body.toLocaleLowerCase();
    const searchableLabel = label.toLocaleLowerCase();
    let matchIndex = searchableBody.indexOf(searchableLabel);
    while (
      matchIndex >= 0
      && occupiedRanges.some(
        (range) => matchIndex < range.end && matchIndex + label.length > range.start,
      )
    ) {
      matchIndex = searchableBody.indexOf(searchableLabel, matchIndex + label.length);
    }

    if (matchIndex >= 0) {
      const matchedLabel = body.slice(matchIndex, matchIndex + label.length);
      const markup = `<a href="${safeAttributeValue(link.Url)}">${matchedLabel}</a>`;
      occupiedRanges.push({ start: matchIndex, end: matchIndex + label.length });
      replacements.push({
        start: matchIndex,
        end: matchIndex + label.length,
        markup,
      });
    }
  }

  let linkedBody = body;
  for (const replacement of replacements.sort((left, right) => right.start - left.start)) {
    linkedBody = `${linkedBody.slice(0, replacement.start)}${replacement.markup}${linkedBody.slice(replacement.end)}`;
  }

  return linkedBody.trimEnd();
}

export function normalizedBodyLinks(
  links: EditableBodyLink[],
  body?: string,
): EditableBodyLink[] {
  const seenDestinations = new Set<string>();
  const searchableBody = body?.toLocaleLowerCase();
  return links
    .map((link, index) => ({
      Url: normalizeEditableLinkUrl(link.Url),
      Anchor_Text: link.Anchor_Text.trim(),
      Display_Order: index,
    }))
    .filter((link) => {
      if (!link.Url || !isSafeLinkDestination(link.Url)) return false;
      if (
        searchableBody !== undefined
        && (
          !link.Anchor_Text
          || !searchableBody.includes(link.Anchor_Text.toLocaleLowerCase())
        )
      ) return false;
      const canonicalUrl = canonicalLinkDestination(link.Url);
      if (seenDestinations.has(canonicalUrl)) return false;
      seenDestinations.add(canonicalUrl);
      return true;
    });
}
