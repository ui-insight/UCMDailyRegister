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

/**
 * Most links staff can keep on one item. Submitters add up to three; staff may
 * add more on the Edit page (#505). Mirrors EditorFinalCreate.Links on the API.
 */
export const EDITOR_MAX_LINKS = 10;

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

/**
 * Identity of a link for de-duplication: the same destination on the same
 * words. Two phrases, or two mentions of one phrase, may point at one
 * destination (#521); a link without a chosen mention matches any mention.
 */
function linkIdentity(url: string, anchorText: string, start?: number): string {
  return `${canonicalLinkDestination(url)}\u0000${anchorText.trim().toLocaleLowerCase()}`
    + `\u0000${start ?? ''}`;
}

export function prepareBodyForEditing(
  body: string,
  storedLinks: StoredLink[] = [],
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
    const safe = isSafeLinkDestination(href);
    // An unsupported destination (http://, a mailto: with a subject) stays in
    // the link list as typed, so the editor reports it instead of the save
    // dropping it without a word (#521).
    const url = safe ? normalizeEditableLinkUrl(href) : href.trim();
    const identity = linkIdentity(url, anchorText, plainStart);
    if (!bodyLinks.some(
      (candidate) => linkIdentity(candidate.Url, candidate.Anchor_Text, candidate.Start) === identity,
    )) {
      bodyLinks.push({
        Url: url,
        Anchor_Text: anchorText,
        Display_Order: bodyLinks.length,
        Start: plainStart,
      });
    }

    if (safe) {
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

  // Editor builds from July and August 2026 silently appended unmatched
  // anchors to the body, each on the line straight after the prose (joined
  // with a single line break). Remove that generated block; the link stays in
  // the link fields, unattached, so staff can put its words back. A link
  // paragraph after a blank line is real call-to-action copy and is kept
  // (#521).
  const bodyLines = plainBody.split('\n');
  let index = bodyLines.length - 1;
  while (index >= 0 && !bodyLines[index].trim()) index -= 1;
  let trailingBlockStart = index + 1;
  while (
    index >= 0
    && standaloneAnchorLabels.has(bodyLines[index].trim().toLocaleLowerCase())
  ) {
    trailingBlockStart = index;
    index -= 1;
  }
  // Those builds appended a link only when they could not find its words
  // (an exact, case-sensitive search), so a line whose words already appear
  // verbatim in the prose is the submitter's own copy and is kept.
  const prose = bodyLines.slice(0, trailingBlockStart).join('\n');
  const blockLines = bodyLines.slice(trailingBlockStart).map((line) => line.trim()).filter(Boolean);
  const legacyBlock = blockLines.length > 0
    && index >= 0
    && bodyLines[index].trim() !== ''
    && blockLines.every((line) => !prose.includes(line));
  plainBody = (legacyBlock ? bodyLines.slice(0, trailingBlockStart).join('\n') : plainBody)
    .trimEnd();

  // A link whose words fell in the trimmed legacy block no longer has a place.
  const links = bodyLinks.map((link) => (
    link.Start !== undefined && link.Start + link.Anchor_Text.length <= plainBody.length
      ? link
      : { ...link, Start: undefined }
  ));
  mergeStoredLinks(plainBody, links, storedLinks);

  // No cap here: a link left out of the editor would be dropped on save.
  return { body: plainBody, links };
}

type StoredLink = { Url: string; Anchor_Text: string | null; Display_Order?: number };

/**
 * Add the item's stored links (the links table, or the AI's embedded links)
 * that the inline anchors do not already cover. Mutates `links`.
 */
function mergeStoredLinks(plainBody: string, links: EditableBodyLink[], storedLinks: StoredLink[]): void {
  for (const link of [...storedLinks].sort(
    (left, right) => (left.Display_Order ?? 0) - (right.Display_Order ?? 0),
  )) {
    const normalizedUrl = normalizeEditableLinkUrl(link.Url);
    const canonicalUrl = canonicalLinkDestination(normalizedUrl);
    const anchorText = link.Anchor_Text?.trim() || '';
    if (!link.Url.trim()) continue;
    const lowerAnchor = anchorText.toLocaleLowerCase();
    if (links.some((candidate) => (
      canonicalLinkDestination(candidate.Url) === canonicalUrl
      && candidate.Anchor_Text.trim().toLocaleLowerCase() === lowerAnchor
    ))) continue;
    // The same destination is already linked. Keep this one as its own link
    // only when its words are in the body and not already a link's words
    // (#521); otherwise it is the stored copy of the inline link.
    if (links.some(
      (candidate) => canonicalLinkDestination(candidate.Url) === canonicalUrl,
    ) && (
      !anchorText
      || findMentions(plainBody, anchorText).length === 0
      || links.some((candidate) => candidate.Anchor_Text.trim().toLocaleLowerCase() === lowerAnchor)
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

/** A typed destination that is a web address, not an email address. */
export function looksLikeWebAddress(value: string): boolean {
  const trimmed = value.trim();
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) || /^www\./i.test(trimmed);
}

/**
 * Links with a destination that can't be saved: not an https:// address or an
 * email address. Saving would otherwise drop them without a word (#505).
 */
export function invalidLinks(links: EditableBodyLink[]): EditableBodyLink[] {
  return links.filter((link) => (
    link.Url.trim()
    && normalizeEditableLinkUrl(link.Url) !== 'mailto:'
    && !isSafeLinkDestination(link.Url)
  ));
}

/**
 * Later links that repeat an earlier link's destination and words (only the
 * first is kept). Different words may share a destination (#521).
 */
export function duplicateLinks(links: EditableBodyLink[]): EditableBodyLink[] {
  const seen = new Set<string>();
  return links.filter((link) => {
    if (!link.Url.trim() || !isSafeLinkDestination(link.Url)) return false;
    const identity = linkIdentity(link.Url, link.Anchor_Text, link.Start);
    if (seen.has(identity)) return true;
    seen.add(identity);
    return false;
  });
}

function linkName(link: EditableBodyLink): string {
  return `"${link.Anchor_Text.trim() || link.Url.trim()}"`;
}

/**
 * Why saving these links would lose one, as a message for staff, or null when
 * every link with a destination will be saved.
 */
export function linkSaveProblem(body: string, links: EditableBodyLink[]): string | null {
  const invalid = invalidLinks(links);
  if (invalid.length) {
    const destinations = invalid.map((link) => `"${link.Url.trim().replace(/^mailto:/, '')}"`).join(', ');
    return `Link destination ${destinations} isn't a web address starting with https:// `
      + 'or an email address, so the link would be lost. Fix the destination or clear the link.';
  }
  const missing = unattachedLinks(body, links);
  if (missing.length) {
    return `Link text ${missing.map(linkName).join(', ')} isn't in the body, so the link would be lost. `
      + 'Add the words to the body, change the link text, or clear the link.';
  }
  const duplicates = duplicateLinks(links);
  if (duplicates.length) {
    return `Link ${duplicates.map(linkName).join(', ')} repeats another link's words and destination, `
      + 'so it would be lost. Change its words or destination, or remove it.';
  }
  const crowded = placeLinks(body, normalizedBodyLinks(links, body)).unplaced;
  if (crowded.length) {
    return `Link text ${crowded.map(linkName).join(', ')} overlaps another link's words, so the link would be lost. `
      + 'Put each link on its own words, or clear one of them.';
  }
  return null;
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
 * or, for words not yet in the body, add them visibly at the end of the last
 * paragraph. Returns the new body and the link pointing at its words.
 *
 * Not on a line of their own: prepareBodyForEditing drops a trailing line
 * that is only a link (what older builds appended), so words added there
 * would vanish on the next load and the link with them (#397).
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
  const appended = [trimmed, next].filter(Boolean).join(' ');
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

interface LinkPlacement {
  replacements: Array<{ start: number; end: number; markup: string }>;
  unplaced: EditableBodyLink[];
}

/** Find a free mention for each link; links whose words are all taken are unplaced. */
function placeLinks(body: string, validLinks: EditableBodyLink[]): LinkPlacement {
  const occupiedRanges: Array<{ start: number; end: number }> = [];
  const replacements: Array<{ start: number; end: number; markup: string }> = [];
  const unplaced: EditableBodyLink[] = [];
  for (const link of validLinks) {
    const label = linkLabel(link);
    if (!label) {
      unplaced.push(link);
      continue;
    }

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
    } else {
      unplaced.push(link);
    }
  }
  return { replacements, unplaced };
}

export function buildLinkedBody(body: string, links: EditableBodyLink[]): string {
  const seenLinks = new Set<string>();
  const validLinks = links
    .map((link, index) => ({
      ...link,
      Url: normalizeEditableLinkUrl(link.Url),
      Display_Order: index,
    }))
    .filter((link) => {
      if (!link.Url || !isSafeLinkDestination(link.Url)) return false;
      const identity = linkIdentity(link.Url, link.Anchor_Text, link.Start);
      if (seenLinks.has(identity)) return false;
      seenLinks.add(identity);
      return true;
    });

  const { replacements } = placeLinks(body, validLinks);

  let linkedBody = body;
  for (const replacement of replacements.sort((left, right) => right.start - left.start)) {
    linkedBody = `${linkedBody.slice(0, replacement.start)}${replacement.markup}${linkedBody.slice(replacement.end)}`;
  }

  return linkedBody.trimEnd();
}

/**
 * The stored body for an edit: plain text with each link written back as an
 * inline anchor, which is what the Word export reads. Check `linkSaveProblem`
 * first, so no link with a destination is left out (#490).
 */
export function linkedBodyForSave(body: string, links: EditableBodyLink[]): string {
  return buildLinkedBody(body, normalizedBodyLinks(links, body)).trim();
}

export function normalizedBodyLinks(
  links: EditableBodyLink[],
  body?: string,
): EditableBodyLink[] {
  const seenLinks = new Set<string>();
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
      const identity = linkIdentity(link.Url, link.Anchor_Text, link.Start);
      if (seenLinks.has(identity)) return false;
      seenLinks.add(identity);
      return true;
    });
}
