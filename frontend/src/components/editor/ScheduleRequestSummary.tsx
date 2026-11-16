import type { ReactNode } from 'react';
import type { SubmissionScheduleRequest, TargetNewsletter } from '../../types/submission';
import { parseISODate } from '../../utils/date';

const RECURRENCE_LABELS: Record<string, string> = {
  once: 'One time',
  weekly: 'Weekly',
  monthly_date: 'Monthly',
  monthly_nth_weekday: 'Monthly (nth weekday)',
  date_range: 'Two-week listing window',
};

/** Repeating schedules saved without an end date run only on their requested date (#477). */
function isOpenEndedRepeat(request: SubmissionScheduleRequest): boolean {
  return ['weekly', 'monthly_date', 'monthly_nth_weekday'].includes(request.Recurrence_Type)
    && !request.Recurrence_End_Date;
}

function formatPublicationDate(value: string): string {
  return parseISODate(value).toLocaleDateString(undefined, {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

interface ScheduleRequestSummaryProps {
  request: SubmissionScheduleRequest;
  targetNewsletter: TargetNewsletter;
  /** Extra controls shown at the end of the date line, such as a Remove button. */
  actions?: ReactNode;
}

function RequestedDates({ request, targetNewsletter }: ScheduleRequestSummaryProps) {
  if (targetNewsletter !== 'both') {
    return <>{request.Requested_Date ? formatPublicationDate(request.Requested_Date) : 'No specific date'}</>;
  }
  return (
    <div className="space-y-0.5">
      {request.Requested_Date && (
        <div>
          <span className="font-normal text-gray-500">Daily Register: </span>
          {formatPublicationDate(request.Requested_Date)}
        </div>
      )}
      {request.Second_Requested_Date && (
        <div>
          <span className="font-normal text-gray-500">My UI: </span>
          {formatPublicationDate(request.Second_Requested_Date)}
        </div>
      )}
      {!request.Requested_Date && !request.Second_Requested_Date && 'No specific date'}
    </div>
  );
}

/**
 * Read-only summary of one requested run schedule: the requested date(s),
 * repeat and recurrence pattern, end date, skipped dates and flexible deadline.
 * Shared by the Edit page's Submission Info card and the Builder's
 * original-entry panel.
 */
export default function ScheduleRequestSummary({
  request,
  targetNewsletter,
  actions,
}: ScheduleRequestSummaryProps) {
  return (
    <>
      <div>
        <RequestedDates request={request} targetNewsletter={targetNewsletter} />
        {request.Repeat_Count > 1 && (
          <span className="font-normal text-gray-500"> &middot; Run {request.Repeat_Count}x</span>
        )}
        {request.Recurrence_Type !== 'once' && (
          <span className="font-normal text-gray-500">
            {' '}
            &middot; {RECURRENCE_LABELS[request.Recurrence_Type] || request.Recurrence_Type}
            {request.Recurrence_Interval > 1 ? ` every ${request.Recurrence_Interval}` : ''}
          </span>
        )}
        {request.Is_Flexible && (
          <span className="ml-1 inline-block px-1.5 py-0.5 text-xs font-normal bg-amber-100 text-amber-700 rounded">Flexible</span>
        )}
        {request.Repeat_Note && (
          <span className="font-normal text-gray-500"> ({request.Repeat_Note})</span>
        )}
        {actions}
      </div>
      {request.Recurrence_End_Date && (
        <div className="text-xs text-gray-500 font-normal mt-0.5">
          Ends: {parseISODate(request.Recurrence_End_Date).toLocaleDateString()}
        </div>
      )}
      {isOpenEndedRepeat(request) && (
        <div className="text-xs text-amber-800 font-normal mt-0.5">
          No end date, so this runs only on its requested date. To repeat it,
          remove this schedule and add a run date with an end date.
        </div>
      )}
      {request.Excluded_Dates.length > 0 && (
        <div className="text-xs text-gray-500 font-normal mt-0.5">
          Skips: {request.Excluded_Dates.join(', ')}
        </div>
      )}
      {request.Is_Flexible && request.Flexible_Deadline && (
        <div className="text-xs text-gray-500 font-normal mt-0.5">Deadline: {request.Flexible_Deadline}</div>
      )}
    </>
  );
}
