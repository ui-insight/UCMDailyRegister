export interface EditableBodyLink {
  Url: string;
  Anchor_Text: string;
  Display_Order?: number;
  /**
   * Offset of the linked words in the plain editing body. Keeps a link on the
   * mention staff chose when the same words appear more than once; when it no
   * longer points at the words, the first free mention is used instead.
   */
  Start?: number;
}

const EMAIL_ADDRESS_PATTERN = /^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$/i;
const ANCHOR_PATTERN = /<a\s+href=["']([^"']+)["'][^>]*>([^<]+)<\/a>/gi;

/** Every inline link in a stored body, in order, with whether it will be clickable. */
export function listBodyLinks(body: string): Array<{ text: string; href: string; safe: boolean }> {
  return [...body.matchAll(ANCHOR_PATTERN)].map((match) => ({
    text: match[2],
    href: match[1],
    safe: isSafeLinkDestination(match[1]),
  }));
}

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
  // Characters removed so far, to map source offsets to plain-body offsets.
  let removedBeforeOffset = 0;
  let plainBody = body.replace(ANCHOR_PATTERN, (
    match,
    href: string,
    anchorText: string,
    offset: number,
    source: string,
  ) => {
    const plainStart = offset - removedBeforeOffset;
    removedBeforeOffset += match.length - anchorText.length;
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
          Start: plainStart,
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

  // A link whose words fell in the trimmed legacy block no longer has a place.
  const links = bodyLinks.map((link) => (
    link.Start !== undefined && link.Start + link.Anchor_Text.length <= plainBody.length
      ? link
      : { ...link, Start: undefined }
  ));
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

/** Start offsets of every case-insensitive, non-overlapping mention of `label`. */
export function findMentions(body: string, label: string): number[] {
  const needle = label.trim().toLocaleLowerCase();
  if (!needle) return [];
  const haystack = body.toLocaleLowerCase();
  const mentions: number[] = [];
  let index = haystack.indexOf(needle);
  while (index >= 0) {
    mentions.push(index);
    index = haystack.indexOf(needle, index + needle.length);
  }
  return mentions;
}

function startsAt(body: string, label: string, start: number | undefined): boolean {
  if (start === undefined || start < 0) return false;
  return body.slice(start, start + label.length).toLocaleLowerCase() === label.toLocaleLowerCase();
}

/** Where a link's words sit in the body: its chosen mention, else the first one. */
export function resolvedLinkStart(body: string, link: EditableBodyLink): number | null {
  const label = link.Anchor_Text.trim();
  if (!label) return null;
  if (startsAt(body, label, link.Start)) return link.Start ?? null;
  const mentions = findMentions(body, label);
  return mentions.length ? mentions[0] : null;
}

/** Links with a destination whose words are not in the body (they would be lost). */
export function unattachedLinks(body: string, links: EditableBodyLink[]): EditableBodyLink[] {
  return links.filter((link) => (
    link.Url.trim()
    && normalizeEditableLinkUrl(link.Url) !== 'mailto:'
    && resolvedLinkStart(body, link) === null
  ));
}

export function synchronizeBodyWithLinkLabel(
  body: string,
  previousLabel: string,
  nextLabel: string,
  start?: number,
): string {
  return commitLinkLabel(body, { Url: '', Anchor_Text: previousLabel, Start: start }, nextLabel).body;
}

/**
 * Apply an edit to a link's words: rewrite them at the link's own mention,
 * or, for words not yet in the body, add them visibly on a new line. Returns
 * the new body and the link pointing at its words.
 */
export function commitLinkLabel(
  body: string,
  link: EditableBodyLink,
  nextLabel: string,
): { body: string; link: EditableBodyLink } {
  const previous = link.Anchor_Text.trim();
  const next = nextLabel.trim().replace(/[<>]/g, '');
  if (!next) return { body, link: { ...link, Anchor_Text: nextLabel, Start: undefined } };

  const placed = (nextBody: string, start: number | null) => ({
    body: nextBody,
    link: { ...link, Anchor_Text: nextLabel, Start: start ?? undefined },
  });

  const previousStart = previous ? resolvedLinkStart(body, link) : null;
  if (previous === next) return placed(body, previousStart);
  if (previousStart !== null) {
    return placed(
      `${body.slice(0, previousStart)}${next}${body.slice(previousStart + previous.length)}`,
      previousStart,
    );
  }

  const existing = findMentions(body, next);
  if (existing.length) return placed(body, existing[0]);
  const trimmed = body.trimEnd();
  const appended = [trimmed, next].filter(Boolean).join('\n');
  return placed(appended, appended.length - next.length);
}

export function synchronizeLinksWithBodyChange(
  previousBody: string,
  nextBody: string,
  links: EditableBodyLink[],
): EditableBodyLink[] {
  // The edit replaced previousBody[prefix, previousBody.length - suffix).
  let prefix = 0;
  const maxPrefix = Math.min(previousBody.length, nextBody.length);
  while (prefix < maxPrefix && previousBody[prefix] === nextBody[prefix]) prefix += 1;
  let suffix = 0;
  while (
    suffix < maxPrefix - prefix
    && previousBody[previousBody.length - 1 - suffix] === nextBody[nextBody.length - 1 - suffix]
  ) suffix += 1;
  const editEnd = previousBody.length - suffix;
  const delta = nextBody.length - previousBody.length;

  return links.map((link) => {
    const label = link.Anchor_Text.trim();
    if (!label) return link;
    const start = resolvedLinkStart(previousBody, link);
    if (start === null) return link;
    const end = start + label.length;

    if (end <= prefix) return { ...link, Start: start };
    if (start >= editEnd) return { ...link, Start: start + delta };

    // The edit touched the linked words: adopt the replacement when it sits
    // exactly where they were.
    const before = previousBody.slice(0, start);
    const after = previousBody.slice(end);
    if (!nextBody.startsWith(before) || !nextBody.endsWith(after)) {
      return { ...link, Start: undefined };
    }
    const replacementEnd = nextBody.length - after.length;
    const replacement = nextBody.slice(before.length, replacementEnd).trim().replace(/[<>]/g, '');
    if (!replacement) return { ...link, Start: undefined };
    const replacementStart = nextBody.indexOf(replacement, before.length);
    return { ...link, Anchor_Text: replacement, Start: replacementStart };
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
    const chosenFree = startsAt(body, label, link.Start) && !occupiedRanges.some(
      (range) => (link.Start ?? 0) < range.end && (link.Start ?? 0) + label.length > range.start,
    );
    let matchIndex = chosenFree ? (link.Start ?? -1) : searchableBody.indexOf(searchableLabel);
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
      ...(link.Start !== undefined ? { Start: link.Start } : {}),
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
