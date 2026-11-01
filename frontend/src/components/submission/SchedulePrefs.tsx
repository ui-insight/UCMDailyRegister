import FieldError from '../common/FieldError';
import { fieldErrorProps, type FieldErrors } from '../../utils/formValidation';
import type { TargetNewsletter } from '../../types/submission';
import { parseISODate, addDaysISO } from '../../utils/date';

interface ScheduleEntry {
  Requested_Date: string;
  Second_Requested_Date: string;
  Repeat_Count: number;
  Repeat_Note: string;
  Is_Flexible: boolean;
  Flexible_Deadline: string;
  Recurrence_Type: 'once' | 'weekly' | 'monthly_date' | 'monthly_nth_weekday' | 'date_range';
  Recurrence_Interval: number;
  Recurrence_End_Date: string;
}

interface Props {
  errors?: FieldErrors;
  schedule: ScheduleEntry;
  onChange: (schedule: ScheduleEntry) => void;
  targetNewsletter: TargetNewsletter;
  validDates?: Set<string>;
  secondaryValidDates?: Set<string>;
  showRecurrenceControls?: boolean;
  showRepeatCount?: boolean;
  heading?: string;
  preferredDateLabel?: string;
  secondDateLabel?: string;
}

function validateDate(
  dateStr: string,
  target: TargetNewsletter,
  validDates?: Set<string>,
): string | null {
  if (!dateStr) return null;

  // If we have server-validated dates, use those
  if (validDates) {
    if (!validDates.has(dateStr)) {
      return 'This date is not a valid publication date. It may be a weekend, holiday, or outside the publication schedule.';
    }
    return null;
  }

  // Fallback: client-side validation
  const d = parseISODate(dateStr);
  const day = d.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat

  if (target === 'myui') {
    if (day !== 1) return 'My UI publishes on Mondays only.';
  } else if (target === 'tdr') {
    if (day === 0 || day === 6) return 'The Daily Register does not publish on weekends.';
  } else if (target === 'both') {
    // For "both", the primary date validates as TDR (weekday)
    if (day === 0 || day === 6) return 'The Daily Register does not publish on weekends.';
  }
  return null;
}

/** Validate a date specifically for My UI (Monday only). */
function validateMyUIDate(dateStr: string): string | null {
  if (!dateStr) return null;
  const d = parseISODate(dateStr);
  if (d.getDay() !== 1) return 'My UI publishes on Mondays only.';
  return null;
}

function getMinDate(): string {
  return addDaysISO(1);
}

function getScheduleErrors({
  errors,
  schedule,
  targetNewsletter,
  validDates,
  secondaryValidDates,
}: Pick<Props, 'schedule' | 'targetNewsletter' | 'validDates' | 'secondaryValidDates'> & { errors: FieldErrors }) {
  const isBoth = targetNewsletter === 'both';
  const primaryId = isBoth ? 'submission-tdr-run-date' : 'submission-preferred-run-date';
  const secondaryId = isBoth ? 'submission-myui-run-date' : 'submission-second-run-date';
  const dateError = errors[primaryId]?.message ?? (isBoth
    ? validateDate(schedule.Requested_Date, 'tdr', validDates)
    : validateDate(schedule.Requested_Date, targetNewsletter, validDates));

  // For "both", validate the second date as Monday-only (My UI)
  const secondDateError = errors[secondaryId]?.message ?? (isBoth
    ? validateDate(schedule.Second_Requested_Date, 'myui', secondaryValidDates) ?? validateMyUIDate(schedule.Second_Requested_Date)
    : schedule.Repeat_Count >= 2 && schedule.Second_Requested_Date
      ? validateDate(schedule.Second_Requested_Date, targetNewsletter, validDates)
      : null);

  const recurrenceEndError = errors['submission-recurrence-end-date']?.message ?? (schedule.Recurrence_Type !== 'once'
    && schedule.Recurrence_End_Date
    && schedule.Recurrence_End_Date < schedule.Requested_Date
      ? 'End date cannot be before the first run date.'
      : null);

  return { dateError, secondDateError, recurrenceEndError };
}

interface DateFieldProps {
  id: string;
  label: string;
  value: string;
  error: string | null;
  hint: string;
  min: string;
  required?: boolean;
  widthClassName?: string;
  onChange: (value: string) => void;
}

function DateField({
  id,
  label,
  value,
  error,
  hint,
  min,
  required = false,
  widthClassName = 'w-full',
  onChange,
}: DateFieldProps) {
  return (
    <>
      <label htmlFor={id} className="block text-xs text-gray-500 mb-1">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={[error ? `${id}-error` : '', `${id}-hint`].filter(Boolean).join(' ')}
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        min={min}
        className={`${widthClassName} rounded-md border px-3 py-2 text-sm focus:ring-1 ${
          error
            ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-ui-gold-500 focus:ring-ui-gold-500'
        }`}
      />
      {error && (
        <p id={`${id}-error`} className="text-xs text-status-error-800 mt-1">{error}</p>
      )}
      <p id={`${id}-hint`} className="text-xs text-gray-600 mt-1">{hint}</p>
    </>
  );
}

export default function SchedulePrefs({
  errors = {},
  schedule,
  onChange,
  targetNewsletter,
  validDates,
  secondaryValidDates,
  showRecurrenceControls = false,
  showRepeatCount = true,
  heading = 'Scheduling Preferences',
  preferredDateLabel = 'Preferred run date',
  secondDateLabel = 'Second run date',
}: Props) {
  const update = (field: keyof ScheduleEntry, value: string | number | boolean) => {
    onChange({ ...schedule, [field]: value });
  };

  const isBoth = targetNewsletter === 'both';
  const { dateError, secondDateError, recurrenceEndError } = getScheduleErrors({
    errors,
    schedule,
    targetNewsletter,
    validDates,
    secondaryValidDates,
  });

  return (
    <div>
      <p className="block text-sm font-medium text-gray-700 mb-2">
        {heading}
      </p>

      {isBoth ? (
        /* --- Both Newsletters: two labeled date pickers --- */
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <DateField
                id="submission-tdr-run-date"
                label="Daily Register run date (Mon–Fri)"
                value={schedule.Requested_Date}
                error={dateError}
                hint="Weekdays only"
                min={getMinDate()}
                required
                onChange={(value) => update('Requested_Date', value)}
              />
            </div>
            <div>
              <DateField
                id="submission-myui-run-date"
                label="My UI run date (Mondays only)"
                value={schedule.Second_Requested_Date}
                error={secondDateError}
                hint="Mondays only"
                min={getMinDate()}
                required
                onChange={(value) => update('Second_Requested_Date', value)}
              />
            </div>
          </div>
          <p className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
            Since you're targeting both newsletters, select a weekday for the Daily Register and a Monday for My UI.
          </p>
        </div>
      ) : (
        /* --- Single newsletter: standard layout --- */
        <>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <DateField
                id="submission-preferred-run-date"
                label={preferredDateLabel}
                value={schedule.Requested_Date}
                error={dateError}
                hint={validDates
                  ? 'Select a valid publication date'
                  : targetNewsletter === 'myui'
                    ? 'My UI publishes Mondays only'
                    : 'Mon–Fri only'}
                min={getMinDate()}
                required
                onChange={(value) => update('Requested_Date', value)}
              />
            </div>
            {showRepeatCount && <div>
              <label
                htmlFor="submission-repeat-count"
                className="block text-xs text-gray-500 mb-1"
              >
                How many times to run
              </label>
              <select
                id="submission-repeat-count"
                {...fieldErrorProps(errors, 'submission-repeat-count')}
                value={schedule.Repeat_Count}
                onChange={(e) => update('Repeat_Count', parseInt(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
              >
                <option value={1}>Once</option>
                <option value={2}>Twice (has RSVP/registration)</option>
              </select>
            </div>}
          </div>
          {showRepeatCount && schedule.Repeat_Count >= 2 && (
            <div className="mt-3">
              <DateField
                id="submission-second-run-date"
                label={secondDateLabel}
                value={schedule.Second_Requested_Date}
                error={secondDateError}
                hint="Select the date for the second run. Must be after the first run date."
                min={schedule.Requested_Date || getMinDate()}
                widthClassName="w-full max-w-xs"
                onChange={(value) => update('Second_Requested_Date', value)}
              />
            </div>
          )}
        </>
      )}

      {showRecurrenceControls ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
          <div>
            <label
              htmlFor="submission-recurrence-type"
              className="block text-xs text-gray-500 mb-1"
            >
              Repeat on a cadence
            </label>
            <select
              id="submission-recurrence-type"
              {...fieldErrorProps(errors, 'submission-recurrence-type')}
              value={schedule.Recurrence_Type}
              onChange={(e) => {
                const recurrenceType = e.target.value as ScheduleEntry['Recurrence_Type'];
                onChange({
                  ...schedule,
                  Recurrence_Type: recurrenceType,
                  Recurrence_Interval: 1,
                  ...(recurrenceType === 'once' ? { Recurrence_End_Date: '' } : {}),
                });
              }}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
            >
              <option value="once">One time</option>
              <option value="weekly">Weekly</option>
              <option value="monthly_date">Monthly on this date</option>
              <option value="monthly_nth_weekday">Monthly on this weekday pattern</option>
            </select>
            <p className="text-xs text-gray-600 mt-1">
              Use this for recurring items like every Friday or first Monday.
            </p>
          </div>
          <div>
            <label
              htmlFor="submission-recurrence-interval"
              className="block text-xs text-gray-500 mb-1"
            >
              Interval
            </label>
            <input
              id="submission-recurrence-interval"
              {...fieldErrorProps(errors, 'submission-recurrence-interval')}
              type="number"
              min={1}
              max={12}
              value={schedule.Recurrence_Interval}
              onChange={(e) => update('Recurrence_Interval', parseInt(e.target.value, 10) || 1)}
              disabled={schedule.Recurrence_Type === 'once'}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500 disabled:bg-gray-50 disabled:text-gray-600"
            />
            <FieldError errors={errors} id="submission-recurrence-interval" />
            <p className="text-xs text-gray-600 mt-1">
              {schedule.Recurrence_Type === 'weekly'
                ? 'Every N weeks'
                : schedule.Recurrence_Type === 'once'
                  ? 'Not used for one-time requests'
                  : 'Every N months'}
            </p>
          </div>
          <div>
            <label
              htmlFor="submission-recurrence-end-date"
              className="block text-xs text-gray-500 mb-1"
            >
              Stop after
            </label>
            <input
              id="submission-recurrence-end-date"
                aria-invalid={recurrenceEndError ? true : undefined}
                aria-describedby={[recurrenceEndError ? 'submission-recurrence-end-date-error' : 'submission-recurrence-end-date-hint'].filter(Boolean).join(' ')}
              type="date"
              value={schedule.Recurrence_End_Date}
              onChange={(e) => update('Recurrence_End_Date', e.target.value)}
              disabled={schedule.Recurrence_Type === 'once'}
              min={schedule.Requested_Date || getMinDate()}
              className={`w-full rounded-md border px-3 py-2 text-sm focus:ring-1 disabled:bg-gray-50 disabled:text-gray-600 ${
                recurrenceEndError
                  ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 focus:border-ui-gold-500 focus:ring-ui-gold-500'
              }`}
            />
            {recurrenceEndError && (
              <p id="submission-recurrence-end-date-error" className="text-xs text-status-error-800 mt-1">{recurrenceEndError}</p>
            )}
            {!recurrenceEndError && (
              <p id="submission-recurrence-end-date-hint" className="text-xs text-gray-600 mt-1">
                Optional. Leave blank to keep running.
              </p>
            )}
          </div>
        </div>
      ) : (
        !isBoth && (
          <div className="mt-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
            <p className="text-xs text-gray-600">
              Recurring scheduling is managed by UCM staff after submission when needed.
            </p>
          </div>
        )
      )}
      <div className="mt-3">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={schedule.Is_Flexible}
            onChange={(e) => {
              const checked = e.target.checked;
              onChange({
                ...schedule,
                Is_Flexible: checked,
                ...(checked ? {} : { Flexible_Deadline: '' }),
              });
            }}
            className="rounded border-gray-300 text-ui-gold-800 focus:ring-ui-gold-500"
          />
          My dates are somewhat flexible
        </label>
        {schedule.Is_Flexible && (
          <div className="mt-2">
          <label htmlFor="submission-flexible-deadline" className="block text-xs text-gray-600 mb-1">Timing flexibility (optional)</label>
          <input
            id="submission-flexible-deadline"
            {...fieldErrorProps(errors, 'submission-flexible-deadline')}
            type="text"
            placeholder="e.g., anytime the week of March 19"
            value={schedule.Flexible_Deadline}
            onChange={(e) => update('Flexible_Deadline', e.target.value)}
            className="mt-2 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          />
          <FieldError errors={errors} id="submission-flexible-deadline" />
          </div>
        )}
      </div>
      <div className="mt-3">
        <label
          htmlFor="submission-scheduling-notes"
          className="block text-xs text-gray-500 mb-1"
        >
          Scheduling notes (optional)
        </label>
        <input
          id="submission-scheduling-notes"
          {...fieldErrorProps(errors, 'submission-scheduling-notes')}
          type="text"
          placeholder="e.g., 'Please skip finals week if needed'"
          value={schedule.Repeat_Note}
          onChange={(e) => update('Repeat_Note', e.target.value)}
          autoComplete="off"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
        />
        <FieldError errors={errors} id="submission-scheduling-notes" />
      </div>
    </div>
  );
}
