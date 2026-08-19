import type { AddScheduleRequestData } from '../api/submissions';
import type { TargetNewsletter } from '../types/submission';

type ScheduledNewsletter = Extract<TargetNewsletter, 'tdr' | 'myui'>;

type RecurrenceData = Pick<
  AddScheduleRequestData,
  'Recurrence_Type' | 'Recurrence_Interval' | 'Recurrence_End_Date'
>;

/** Map an editor's newsletter choice onto the existing two-date backend contract. */
export function buildEditorScheduleRequest(
  targetNewsletter: TargetNewsletter,
  newsletter: ScheduledNewsletter,
  date: string,
  recurrence?: RecurrenceData,
): AddScheduleRequestData {
  if (targetNewsletter === 'both' && newsletter === 'myui') {
    return {
      Requested_Date: null,
      Second_Requested_Date: date,
      ...(recurrence ?? {}),
    };
  }

  return {
    Requested_Date: date,
    ...(recurrence ?? {}),
  };
}
