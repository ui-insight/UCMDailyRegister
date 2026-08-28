/**
 * Weekly SLC digest assembly.
 *
 * Turns SLC calendar submissions (Show_In_SLC_Calendar=true, hydrated
 * Occurrence_Dates from the recurrence-aware week query) into a per-day
 * digest plus the Outlook-ready rich-text (HTML) and plain-text clipboard
 * payloads. SLC submission bodies are label/value lines written by three
 * producers — the Trumba harvest promotion ("Start time"), the workbook
 * importer ("Start time"), and the manual SLC submit form ("Start Time") —
 * so field lookup is case-insensitive.
 *
 * The copied HTML uses inline styles only: Outlook's rendering engine
 * ignores CSS classes and style blocks on paste.
 */

import type { EventClassification, Submission } from '../types/submission';
import { addDaysToISODate, parseISODate, toISODate } from './date';
import { getOccurrenceDates } from './submissionOccurrences';

export interface DigestEvent {
  submission: Submission;
  time: string | null;
  location: string | null;
  url: string | null;
  classification: EventClassification | null;
}

export interface DigestDay {
  date: string;
  events: DigestEvent[];
}

const UI_BLACK = '#323232';
const UI_SILVER = '#808080';
const CLEARWATER = '#005555';
const GOLD_DARK = '#A87700';

const CLASSIFICATION_LABELS: Record<EventClassification, string> = {
  strategic: 'Strategic',
  signature: 'Signature',
};

const CLASSIFICATION_COLORS: Record<EventClassification, string> = {
  strategic: CLEARWATER,
  signature: GOLD_DARK,
};

/** Monday of the week containing the given date. */
export function weekStartOf(d: Date): string {
  const copy = new Date(d);
  copy.setDate(copy.getDate() - ((copy.getDay() + 6) % 7));
  return toISODate(copy);
}

/** Monday of next week — the digest's default, since Cami preps the coming week's email. */
export function defaultDigestWeekStart(today: Date = new Date()): string {
  return addDaysToISODate(weekStartOf(today), 7);
}

/** Parse "Label: value" body lines into a lowercase-keyed lookup. */
export function parseBodyFields(body: string): Map<string, string> {
  const fields = new Map<string, string>();
  for (const line of body.split('\n')) {
    const separator = line.indexOf(':');
    if (separator <= 0) continue;
    const key = line.slice(0, separator).trim().toLowerCase();
    const value = line.slice(separator + 1).trim();
    if (key && value && !fields.has(key)) fields.set(key, value);
  }
  return fields;
}

export function toDigestEvent(submission: Submission): DigestEvent {
  const fields = parseBodyFields(submission.Original_Body);
  const linkUrl = submission.Links[0]?.Url ?? null;
  return {
    submission,
    time: fields.get('start time') ?? null,
    location: fields.get('location') ?? null,
    url: linkUrl ?? fields.get('event page') ?? null,
    classification: submission.Event_Classification,
  };
}

/** Sort key for within-day ordering: all-day/untimed first, then by clock time. */
function timeSortValue(time: string | null): number {
  if (!time || /all day/i.test(time)) return -1;
  const match = /(\d{1,2})(?::(\d{2}))?\s*([ap])/i.exec(time);
  if (!match) return Number.MAX_SAFE_INTEGER;
  let hours = parseInt(match[1], 10) % 12;
  if (match[3].toLowerCase() === 'p') hours += 12;
  return hours * 60 + parseInt(match[2] ?? '0', 10);
}

/**
 * Group SLC submissions into the digest's day buckets for one week.
 *
 * Multi-day and recurring submissions land in every day bucket their
 * hydrated occurrences fall on, so an event spanning Wednesday–Friday
 * appears under all three days. Days without events are omitted.
 */
export function buildDigestDays(
  submissions: Submission[],
  weekStartISO: string,
): DigestDay[] {
  const weekEndISO = addDaysToISODate(weekStartISO, 6);
  const byDay = new Map<string, DigestEvent[]>();
  for (const submission of submissions) {
    const event = toDigestEvent(submission);
    for (const dateKey of getOccurrenceDates(submission)) {
      if (dateKey < weekStartISO || dateKey > weekEndISO) continue;
      if (!byDay.has(dateKey)) byDay.set(dateKey, []);
      byDay.get(dateKey)!.push(event);
    }
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, events]) => ({
      date,
      events: events.sort(
        (a, b) =>
          timeSortValue(a.time) - timeSortValue(b.time)
          || a.submission.Original_Headline.localeCompare(b.submission.Original_Headline),
      ),
    }));
}

export function formatDayHeading(dateISO: string): string {
  return parseISODate(dateISO).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

/** "September 7 – 13, 2026", spelling out months/years when the week crosses them. */
export function formatWeekRange(weekStartISO: string): string {
  const start = parseISODate(weekStartISO);
  const end = parseISODate(addDaysToISODate(weekStartISO, 6));
  const startMonth = start.toLocaleDateString('en-US', { month: 'long' });
  const endMonth = end.toLocaleDateString('en-US', { month: 'long' });
  if (start.getFullYear() !== end.getFullYear()) {
    return `${startMonth} ${start.getDate()}, ${start.getFullYear()} – ${endMonth} ${end.getDate()}, ${end.getFullYear()}`;
  }
  if (startMonth !== endMonth) {
    return `${startMonth} ${start.getDate()} – ${endMonth} ${end.getDate()}, ${end.getFullYear()}`;
  }
  return `${startMonth} ${start.getDate()} – ${end.getDate()}, ${end.getFullYear()}`;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function eventDetailLine(event: DigestEvent): string | null {
  const parts = [event.time, event.location].filter(
    (part): part is string => Boolean(part),
  );
  return parts.length > 0 ? parts.join(' · ') : null;
}

export function buildDigestHtml(weekStartISO: string, days: DigestDay[]): string {
  const lines: string[] = [
    `<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt;color:${UI_BLACK};">`,
    '<p style="font-size:14pt;font-weight:bold;margin:0 0 2px;">Senior Leadership Council Events</p>',
    `<p style="color:${UI_SILVER};margin:0 0 16px;">Week of ${escapeHtml(formatWeekRange(weekStartISO))}</p>`,
  ];
  for (const day of days) {
    lines.push(
      `<p style="font-size:12pt;font-weight:bold;color:${CLEARWATER};margin:16px 0 6px;">`
      + `${escapeHtml(formatDayHeading(day.date))}</p>`,
    );
    for (const event of day.events) {
      const title = escapeHtml(event.submission.Original_Headline);
      const titleHtml = event.url
        ? `<a href="${escapeHtml(event.url)}" style="color:${CLEARWATER};"><b>${title}</b></a>`
        : `<b>${title}</b>`;
      const tag = event.classification
        ? ` <span style="color:${CLASSIFICATION_COLORS[event.classification]};font-weight:bold;">`
          + `[${CLASSIFICATION_LABELS[event.classification]}]</span>`
        : '';
      lines.push(`<p style="margin:0 0 1px;">${titleHtml}${tag}</p>`);
      const detail = eventDetailLine(event);
      lines.push(
        `<p style="margin:0 0 10px;color:${UI_SILVER};">${detail ? escapeHtml(detail) : ''}</p>`,
      );
    }
  }
  lines.push('</div>');
  return lines.join('\n');
}

export function buildDigestText(weekStartISO: string, days: DigestDay[]): string {
  const lines: string[] = [
    'SENIOR LEADERSHIP COUNCIL EVENTS',
    `Week of ${formatWeekRange(weekStartISO)}`,
  ];
  for (const day of days) {
    lines.push('', formatDayHeading(day.date).toUpperCase(), '');
    for (const event of day.events) {
      const tag = event.classification
        ? ` [${CLASSIFICATION_LABELS[event.classification]}]`
        : '';
      lines.push(`${event.submission.Original_Headline}${tag}`);
      const detail = eventDetailLine(event);
      if (detail) lines.push(detail);
      if (event.url) lines.push(event.url);
      lines.push('');
    }
  }
  return lines.join('\n').trimEnd() + '\n';
}
