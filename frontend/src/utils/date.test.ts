import { describe, it, expect, afterEach, vi } from 'vitest';
import { parseISODate, toISODate, todayISO, addDaysISO, addMonthsISO } from './date';

afterEach(() => {
  vi.useRealTimers();
});

describe('parseISODate', () => {
  it('keeps the calendar date in the local timezone', () => {
    const d = parseISODate('2026-07-20');
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(6);
    expect(d.getDate()).toBe(20);
  });

  it('renders the correct weekday for a Monday', () => {
    // 2026-07-20 is a Monday; UTC parsing would render Sunday in US timezones
    expect(parseISODate('2026-07-20').getDay()).toBe(1);
  });
});

describe('toISODate', () => {
  it('round-trips with parseISODate', () => {
    expect(toISODate(parseISODate('2026-02-28'))).toBe('2026-02-28');
    expect(toISODate(parseISODate('2026-12-31'))).toBe('2026-12-31');
  });

  it('uses the local calendar date, not UTC', () => {
    // 23:30 local on Jul 17 is already Jul 18 in UTC for US timezones;
    // toISODate must still report the local date.
    const lateEvening = new Date(2026, 6, 17, 23, 30, 0);
    expect(toISODate(lateEvening)).toBe('2026-07-17');
    expect(lateEvening.toISOString().split('T')[0]).not.toBe('2026-07-17');
  });
});

describe('today/offset helpers', () => {
  it('computes today, tomorrow, and month offsets in local time', () => {
    vi.useFakeTimers({ now: new Date(2026, 6, 17, 22, 0, 0) });
    expect(todayISO()).toBe('2026-07-17');
    expect(addDaysISO(1)).toBe('2026-07-18');
    expect(addDaysISO(90)).toBe('2026-10-15');
    expect(addMonthsISO(3)).toBe('2026-10-17');
  });
});
