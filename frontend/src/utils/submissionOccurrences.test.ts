import { describe, expect, it } from 'vitest';
import type { Submission } from '../types/submission';
import { getOccurrenceDates, getPrimaryOccurrenceDate } from './submissionOccurrences';

const baseSubmission: Submission = {
  Id: 'submission-1',
  Category: 'faculty_staff',
  Target_Newsletter: 'tdr',
  Original_Headline: 'Parking lot closure',
  Original_Body: 'Lot 1 will close for maintenance.',
  Submitter_Name: 'Jane Editor',
  Submitter_Email: 'jane@example.edu',
  Submitter_Notes: null,
  Assigned_Editor: null,
  Editorial_Notes: null,
  Survey_End_Date: null,
  Has_Image: false,
  Image_Path: null,
  Status: 'new',
  Show_In_SLC_Calendar: false,
  Event_Classification: null,
  Created_At: '2026-01-01T12:00:00Z',
  Updated_At: '2026-01-01T12:00:00Z',
  Links: [],
  Schedule_Requests: [],
  Occurrence_Dates: [],
};

describe('submission occurrence helpers', () => {
  it('prefers persisted occurrence dates when present', () => {
    const submission: Submission = {
      ...baseSubmission,
      Occurrence_Dates: ['2026-02-02', '2026-02-09'],
      Schedule_Requests: [
        {
          Id: 'schedule-1',
          Requested_Date: '2026-03-01',
          Second_Requested_Date: null,
          Repeat_Count: 1,
          Repeat_Note: null,
          Is_Flexible: false,
          Flexible_Deadline: null,
          Recurrence_Type: 'once',
          Recurrence_Interval: 1,
          Recurrence_End_Date: null,
          Excluded_Dates: [],
          Occurrence_Dates: ['2026-03-01'],
        },
      ],
    };

    expect(getOccurrenceDates(submission)).toEqual(['2026-02-02', '2026-02-09']);
    expect(getPrimaryOccurrenceDate(submission)).toBe('2026-02-02');
  });

  it('falls back to schedule request dates', () => {
    const submission: Submission = {
      ...baseSubmission,
      Schedule_Requests: [
        {
          Id: 'schedule-1',
          Requested_Date: '2026-04-06',
          Second_Requested_Date: null,
          Repeat_Count: 1,
          Repeat_Note: null,
          Is_Flexible: false,
          Flexible_Deadline: null,
          Recurrence_Type: 'weekly',
          Recurrence_Interval: 1,
          Recurrence_End_Date: null,
          Excluded_Dates: [],
          Occurrence_Dates: ['2026-04-06', '2026-04-13'],
        },
        {
          Id: 'schedule-2',
          Requested_Date: '2026-04-20',
          Second_Requested_Date: null,
          Repeat_Count: 1,
          Repeat_Note: null,
          Is_Flexible: false,
          Flexible_Deadline: null,
          Recurrence_Type: 'once',
          Recurrence_Interval: 1,
          Recurrence_End_Date: null,
          Excluded_Dates: [],
          Occurrence_Dates: [],
        },
      ],
    };

    expect(getOccurrenceDates(submission)).toEqual([
      '2026-04-06',
      '2026-04-13',
      '2026-04-20',
    ]);
  });
});
