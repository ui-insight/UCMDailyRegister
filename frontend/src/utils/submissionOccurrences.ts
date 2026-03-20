import type { Submission } from '../types/submission';

export function getOccurrenceDates(submission: Submission): string[] {
  if (submission.Occurrence_Dates.length > 0) {
    return submission.Occurrence_Dates;
  }

  const scheduleOccurrences = submission.Schedule_Requests.flatMap((request) => (
    request.Occurrence_Dates.length > 0
      ? request.Occurrence_Dates
      : [request.Requested_Date]
  ));

  return scheduleOccurrences
    .filter((date): date is string => Boolean(date));
}


export function getPrimaryOccurrenceDate(submission: Submission): string | null {
  const dates = getOccurrenceDates(submission);
  return dates.length > 0 ? dates[0] : null;
}
