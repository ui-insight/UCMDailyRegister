/**
 * Helpers for date-only strings (YYYY-MM-DD).
 *
 * `new Date('YYYY-MM-DD')` parses as UTC midnight, which renders as the
 * previous calendar day in US timezones. Likewise `toISOString()` converts
 * to UTC, so local evening times roll forward a day. Always go through
 * these helpers when converting between Date objects and date-only strings.
 */

/** Parse a YYYY-MM-DD string as local time (noon avoids DST edge cases). */
export function parseISODate(dateStr: string): Date {
  return new Date(`${dateStr}T12:00:00`);
}

/** Format a Date as YYYY-MM-DD using the local calendar date. */
export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Today's local date as YYYY-MM-DD. */
export function todayISO(): string {
  return toISODate(new Date());
}

/** The local date `days` days from today as YYYY-MM-DD. */
export function addDaysISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return toISODate(d);
}

/** The local date `months` months from today as YYYY-MM-DD. */
export function addMonthsISO(months: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() + months);
  return toISODate(d);
}
