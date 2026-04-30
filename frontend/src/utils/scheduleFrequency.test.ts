import { describe, expect, it } from 'vitest';
import { formatScheduleFrequency } from './scheduleFrequency';

describe('formatScheduleFrequency', () => {
  it('uses backend Python weekday numbers for weekly schedules', () => {
    expect(formatScheduleFrequency({
      Is_Daily: false,
      Publish_Day_Of_Week: 0,
      Mode: 'academic_year',
    })).toBe('Weekly (Monday)');
    expect(formatScheduleFrequency({
      Is_Daily: false,
      Publish_Day_Of_Week: 6,
      Mode: 'academic_year',
    })).toBe('Weekly (Sunday)');
  });

  it('formats daily and custom-date schedules', () => {
    expect(formatScheduleFrequency({
      Is_Daily: true,
      Publish_Day_Of_Week: null,
      Mode: 'academic_year',
    })).toBe('Daily (weekdays)');
    expect(formatScheduleFrequency({
      Is_Daily: false,
      Publish_Day_Of_Week: null,
      Mode: 'winter_break',
    })).toBe('Custom dates');
  });
});
