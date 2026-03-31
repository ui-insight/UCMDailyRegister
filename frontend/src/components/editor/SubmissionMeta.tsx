import { useCallback, useEffect, useState } from 'react';
import type { Submission, TargetNewsletter } from '../../types/submission';
import { getValidDates } from '../../api/schedule';

interface SubmissionMetaProps {
  submission: Submission;
  onChangeNewsletter?: (target: TargetNewsletter) => void;
  onSkipOccurrence?: (scheduleId: string, occurrenceDate: string) => Promise<void>;
  onRescheduleOccurrence?: (
    scheduleId: string,
    occurrenceDate: string,
    newDate: string,
  ) => Promise<void>;
  onAddScheduleDate?: (newsletter: string, date: string) => Promise<void>;
  occurrenceActionLoading?: boolean;
}

const CATEGORY_LABELS: Record<string, string> = {
  faculty_staff: 'Faculty/Staff',
  student: 'Student',
  employee_announcement: 'Employee Announcement',
  job_opportunity: 'Job Opportunity',
  survey: 'Survey',
  kudos: 'Kudos',
  in_memoriam: 'In Memoriam',
  news_release: 'News Release',
  calendar_event: 'Calendar Event',
};

const TARGET_LABELS: Record<string, string> = {
  tdr: 'The Daily Register',
  myui: 'My UI',
  both: 'Both Newsletters',
};

const RECURRENCE_LABELS: Record<string, string> = {
  once: 'One time',
  weekly: 'Weekly',
  monthly_date: 'Monthly',
  monthly_nth_weekday: 'Monthly (nth weekday)',
};

export default function SubmissionMeta({
  submission,
  onChangeNewsletter,
  onSkipOccurrence,
  onRescheduleOccurrence,
  onAddScheduleDate,
  occurrenceActionLoading = false,
}: SubmissionMetaProps) {
  const [rescheduleTarget, setRescheduleTarget] = useState<{
    scheduleId: string;
    occurrenceDate: string;
  } | null>(null);
  const [replacementDate, setReplacementDate] = useState('');

  const [showAddDate, setShowAddDate] = useState(false);
  const [addDateNewsletter, setAddDateNewsletter] = useState('');
  const [addDateValue, setAddDateValue] = useState('');
  const [addDateLoading, setAddDateLoading] = useState(false);
  const [addDateError, setAddDateError] = useState('');
  const [validDatesSet, setValidDatesSet] = useState<Set<string>>(new Set());

  const getMinDate = () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  };

  const getMaxDate = () => {
    const d = new Date();
    d.setDate(d.getDate() + 90);
    return d.toISOString().split('T')[0];
  };

  const resolveNewsletter = useCallback(() => {
    if (submission.Target_Newsletter === 'both') return addDateNewsletter;
    return submission.Target_Newsletter;
  }, [submission.Target_Newsletter, addDateNewsletter]);

  useEffect(() => {
    if (!showAddDate) return;
    const nl = resolveNewsletter();
    if (!nl) {
      setValidDatesSet(new Set());
      return;
    }
    let cancelled = false;
    getValidDates(getMinDate(), getMaxDate(), nl).then((resp) => {
      if (cancelled) return;
      const dates = new Set(resp.dates.map((d) => d.date));
      setValidDatesSet(dates);
    });
    return () => { cancelled = true; };
  }, [showAddDate, addDateNewsletter, submission.Target_Newsletter, resolveNewsletter]);

  const handleOpenAddDate = () => {
    setShowAddDate(true);
    setAddDateValue('');
    setAddDateError('');
    setAddDateNewsletter(submission.Target_Newsletter === 'both' ? '' : submission.Target_Newsletter);
  };

  const handleCancelAddDate = () => {
    setShowAddDate(false);
    setAddDateValue('');
    setAddDateError('');
    setAddDateNewsletter('');
  };

  const handleSaveAddDate = async () => {
    const nl = resolveNewsletter();
    if (!nl || !addDateValue || !onAddScheduleDate) return;
    if (!validDatesSet.has(addDateValue)) {
      const label = nl === 'myui' ? 'My UI (Mondays only)' : 'The Daily Register';
      setAddDateError(`Not a valid publication date for ${label}.`);
      return;
    }
    setAddDateLoading(true);
    setAddDateError('');
    try {
      await onAddScheduleDate(nl, addDateValue);
      handleCancelAddDate();
    } catch (err) {
      setAddDateError(err instanceof Error ? err.message : 'Failed to add date');
    } finally {
      setAddDateLoading(false);
    }
  };

  const handleStartReschedule = (scheduleId: string, occurrenceDate: string) => {
    setRescheduleTarget({ scheduleId, occurrenceDate });
    setReplacementDate(occurrenceDate);
  };

  const handleCancelReschedule = () => {
    setRescheduleTarget(null);
    setReplacementDate('');
  };

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Submission Info</h3>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-xs text-gray-500">Submitter</dt>
          <dd className="text-gray-900">{submission.Submitter_Name}</dd>
          <dd className="text-xs text-gray-500">{submission.Submitter_Email}</dd>
          {submission.Status === 'pending_info' && (
            <dd className="mt-1">
              <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">
                Info requested
              </span>
            </dd>
          )}
        </div>
        <div>
          <dt className="text-xs text-gray-500">Target Newsletter</dt>
          {onChangeNewsletter ? (
            <dd>
              <select
                value={submission.Target_Newsletter}
                onChange={(e) => onChangeNewsletter(e.target.value as TargetNewsletter)}
                className="mt-0.5 w-full rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
              >
                {Object.entries(TARGET_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>{label}</option>
                ))}
              </select>
            </dd>
          ) : (
            <dd className="text-gray-900">
              {TARGET_LABELS[submission.Target_Newsletter] || submission.Target_Newsletter}
            </dd>
          )}
        </div>
        <div>
          <dt className="text-xs text-gray-500">Category</dt>
          <dd className="text-gray-900">
            {CATEGORY_LABELS[submission.Category] || submission.Category}
          </dd>
        </div>
        {submission.Survey_End_Date && (
          <div>
            <dt className="text-xs text-gray-500">Survey Ends</dt>
            <dd className="text-gray-900">
              {new Date(submission.Survey_End_Date).toLocaleDateString(undefined, {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </dd>
          </div>
        )}
        {submission.Schedule_Requests.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500">Requested Run Date</dt>
            {submission.Schedule_Requests.map((req) => (
              <dd key={req.Id} className="mt-1 text-gray-900 font-medium">
                <div>
                  {req.Requested_Date
                    ? new Date(req.Requested_Date).toLocaleDateString(undefined, {
                        weekday: 'short',
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })
                    : 'No specific date'}
                  {req.Repeat_Count > 1 && (
                    <span className="font-normal text-gray-500"> &middot; Run {req.Repeat_Count}x</span>
                  )}
                  {req.Recurrence_Type !== 'once' && (
                    <span className="font-normal text-gray-500">
                      {' '}
                      &middot; {RECURRENCE_LABELS[req.Recurrence_Type] || req.Recurrence_Type}
                      {req.Recurrence_Interval > 1 ? ` every ${req.Recurrence_Interval}` : ''}
                    </span>
                  )}
                  {req.Is_Flexible && (
                    <span className="ml-1 inline-block px-1.5 py-0.5 text-xs font-normal bg-amber-100 text-amber-700 rounded">Flexible</span>
                  )}
                  {req.Repeat_Note && (
                    <span className="font-normal text-gray-500"> ({req.Repeat_Note})</span>
                  )}
                </div>
                {req.Recurrence_End_Date && (
                  <div className="text-xs text-gray-500 font-normal mt-0.5">
                    Ends: {new Date(req.Recurrence_End_Date).toLocaleDateString()}
                  </div>
                )}
                {req.Excluded_Dates.length > 0 && (
                  <div className="text-xs text-gray-500 font-normal mt-0.5">
                    Skips: {req.Excluded_Dates.join(', ')}
                  </div>
                )}
                {req.Is_Flexible && req.Flexible_Deadline && (
                  <div className="text-xs text-gray-500 font-normal mt-0.5">Deadline: {req.Flexible_Deadline}</div>
                )}
                {req.Occurrence_Dates.length > 0 && (
                  <div className="mt-2 rounded-md bg-gray-50 p-2">
                    <div className="text-[11px] uppercase tracking-wide text-gray-500 mb-0.5">
                      Upcoming occurrences
                    </div>
                    <div className="text-[10px] text-gray-400 mb-1">
                      Skip Date removes this item from that day's newsletter. Move reschedules it.
                    </div>
                    <div className="space-y-2">
                      {req.Occurrence_Dates.map((occurrenceDate) => (
                        <div key={`${req.Id}-${occurrenceDate}`} className="flex flex-col gap-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-normal text-gray-700">
                              {new Date(`${occurrenceDate}T12:00:00`).toLocaleDateString(undefined, {
                                weekday: 'short',
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                              })}
                            </span>
                            {(onSkipOccurrence || onRescheduleOccurrence) && (
                              <div className="flex items-center gap-2">
                                {onSkipOccurrence && (
                                  <button
                                    type="button"
                                    onClick={() => onSkipOccurrence(req.Id, occurrenceDate)}
                                    disabled={occurrenceActionLoading}
                                    title="Don't publish this item on this date"
                                    className="text-xs rounded border border-gray-300 px-2 py-1 text-gray-700 hover:bg-white disabled:opacity-50"
                                  >
                                    Skip Date
                                  </button>
                                )}
                                {onRescheduleOccurrence && (
                                  <button
                                    type="button"
                                    onClick={() => handleStartReschedule(req.Id, occurrenceDate)}
                                    disabled={occurrenceActionLoading}
                                    className="text-xs rounded border border-ui-gold-200 bg-ui-gold-50 px-2 py-1 text-ui-gold-700 hover:bg-ui-gold-100 disabled:opacity-50"
                                  >
                                    Move
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                          {rescheduleTarget?.scheduleId === req.Id
                            && rescheduleTarget.occurrenceDate === occurrenceDate
                            && onRescheduleOccurrence && (
                              <div className="flex items-center gap-2">
                                <input
                                  type="date"
                                  value={replacementDate}
                                  min={getMinDate()}
                                  onChange={(e) => setReplacementDate(e.target.value)}
                                  className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-xs focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                                />
                                <button
                                  type="button"
                                  onClick={async () => {
                                    if (!replacementDate) return;
                                    await onRescheduleOccurrence(req.Id, occurrenceDate, replacementDate);
                                    handleCancelReschedule();
                                  }}
                                  disabled={occurrenceActionLoading || !replacementDate}
                                  className="text-xs rounded bg-ui-gold-600 px-2 py-1 text-white hover:bg-ui-gold-700 disabled:opacity-50"
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  onClick={handleCancelReschedule}
                                  disabled={occurrenceActionLoading}
                                  className="text-xs rounded border border-gray-300 px-2 py-1 text-gray-600 hover:bg-white disabled:opacity-50"
                                >
                                  Cancel
                                </button>
                              </div>
                            )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </dd>
            ))}
          </div>
        )}
        {onAddScheduleDate && !showAddDate && (
          <div>
            <button
              type="button"
              onClick={handleOpenAddDate}
              className="text-xs rounded border border-dashed border-gray-300 px-3 py-1.5 text-gray-600 hover:border-ui-gold-400 hover:text-ui-gold-700 hover:bg-ui-gold-50 w-full"
            >
              + Add Run Date
            </button>
          </div>
        )}
        {onAddScheduleDate && showAddDate && (
          <div className="rounded-md border border-ui-gold-200 bg-ui-gold-50 p-3 space-y-2">
            <div className="text-xs font-medium text-gray-700">Add Run Date</div>
            {submission.Target_Newsletter === 'both' && (
              <div className="flex gap-3">
                <label className="flex items-center gap-1 text-xs text-gray-700">
                  <input
                    type="radio"
                    name="addDateNewsletter"
                    value="tdr"
                    checked={addDateNewsletter === 'tdr'}
                    onChange={() => { setAddDateNewsletter('tdr'); setAddDateValue(''); setAddDateError(''); }}
                    className="accent-ui-gold-600"
                  />
                  Daily Register
                </label>
                <label className="flex items-center gap-1 text-xs text-gray-700">
                  <input
                    type="radio"
                    name="addDateNewsletter"
                    value="myui"
                    checked={addDateNewsletter === 'myui'}
                    onChange={() => { setAddDateNewsletter('myui'); setAddDateValue(''); setAddDateError(''); }}
                    className="accent-ui-gold-600"
                  />
                  My UI
                </label>
              </div>
            )}
            {(submission.Target_Newsletter !== 'both' || addDateNewsletter) && (
              <>
                <input
                  type="date"
                  value={addDateValue}
                  min={getMinDate()}
                  max={getMaxDate()}
                  onChange={(e) => { setAddDateValue(e.target.value); setAddDateError(''); }}
                  className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
                {addDateValue && validDatesSet.size > 0 && validDatesSet.has(addDateValue) && (
                  <div className="text-[10px] text-green-600">Valid publication date</div>
                )}
                {addDateError && (
                  <div className="text-[10px] text-red-600">{addDateError}</div>
                )}
              </>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSaveAddDate}
                disabled={addDateLoading || !addDateValue || !resolveNewsletter()}
                className="text-xs rounded bg-ui-gold-600 px-3 py-1 text-white hover:bg-ui-gold-700 disabled:opacity-50"
              >
                {addDateLoading ? 'Saving...' : 'Save'}
              </button>
              <button
                type="button"
                onClick={handleCancelAddDate}
                disabled={addDateLoading}
                className="text-xs rounded border border-gray-300 px-3 py-1 text-gray-600 hover:bg-white disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
        <div>
          <dt className="text-xs text-gray-500">Submitted</dt>
          <dd className="text-gray-900">
            {new Date(submission.Created_At.endsWith('Z') ? submission.Created_At : submission.Created_At + 'Z').toLocaleString()}
          </dd>
        </div>
        {submission.Links.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500">Links</dt>
            {submission.Links.map((link) => (
              <dd key={link.Id} className="text-xs">
                <a
                  href={link.Url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all"
                >
                  {link.Anchor_Text || link.Url}
                </a>
              </dd>
            ))}
          </div>
        )}
        {submission.Submitter_Notes && (
          <div>
            <dt className="text-xs text-gray-500">Submitter Notes</dt>
            <dd className="text-gray-700 text-xs bg-gray-50 p-2 rounded mt-1">
              {submission.Submitter_Notes}
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}
