// Display helpers shared by the harvested-event triage pages (SLC and ops).

import { toISODate } from './date';

interface CategorizedEvent {
  Category_Path: string | null;
}

interface ScheduledEvent {
  Event_Start: string;
  Event_End: string | null;
  All_Day: boolean;
}

export function topCategory(event: CategorizedEvent): string {
  return event.Category_Path?.split('|')[0] ?? 'Uncategorized';
}

export function weekStartKey(isoDateTime: string): string {
  const d = new Date(isoDateTime);
  const daysSinceMonday = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - daysSinceMonday);
  return toISODate(d);
}

export function formatWeekHeading(weekStartISO: string): string {
  return `Week of ${new Date(weekStartISO + 'T12:00:00').toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })}`;
}

export function formatEventDate(event: ScheduledEvent): string {
  return new Date(event.Event_Start).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

export function formatEventTime(event: ScheduledEvent): string {
  if (event.All_Day) return 'All day';
  const timeOptions: Intl.DateTimeFormatOptions = { hour: 'numeric', minute: '2-digit' };
  const start = new Date(event.Event_Start).toLocaleTimeString('en-US', timeOptions);
  if (!event.Event_End) return start;
  const end = new Date(event.Event_End).toLocaleTimeString('en-US', timeOptions);
  return `${start} – ${end}`;
}
