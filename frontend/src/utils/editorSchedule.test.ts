import { describe, expect, it } from 'vitest';
import { buildEditorScheduleRequest } from './editorSchedule';

describe('buildEditorScheduleRequest', () => {
  it('stores a Daily Register date in the primary date field', () => {
    expect(buildEditorScheduleRequest('both', 'tdr', '2026-05-05')).toEqual({
      Requested_Date: '2026-05-05',
    });
  });

  it('stores a My UI date for a both-newsletters submission in the secondary field', () => {
    expect(buildEditorScheduleRequest('both', 'myui', '2026-05-04')).toEqual({
      Requested_Date: null,
      Second_Requested_Date: '2026-05-04',
    });
  });

  it('keeps the primary field contract for a My UI-only submission', () => {
    expect(buildEditorScheduleRequest('myui', 'myui', '2026-05-04')).toEqual({
      Requested_Date: '2026-05-04',
    });
  });

  it('preserves recurrence settings for the selected newsletter', () => {
    expect(
      buildEditorScheduleRequest('both', 'myui', '2026-05-04', {
        Recurrence_Type: 'weekly',
        Recurrence_Interval: 2,
        Recurrence_End_Date: '2026-06-29',
      }),
    ).toEqual({
      Requested_Date: null,
      Second_Requested_Date: '2026-05-04',
      Recurrence_Type: 'weekly',
      Recurrence_Interval: 2,
      Recurrence_End_Date: '2026-06-29',
    });
  });
});
