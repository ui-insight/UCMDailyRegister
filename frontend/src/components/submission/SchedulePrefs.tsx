import type { TargetNewsletter } from '../../types/submission';

interface ScheduleEntry {
  Requested_Date: string;
  Repeat_Count: number;
  Repeat_Note: string;
  Is_Flexible: boolean;
  Flexible_Deadline: string;
  Recurrence_Type: 'once' | 'weekly' | 'monthly_date' | 'monthly_nth_weekday';
  Recurrence_Interval: number;
  Recurrence_End_Date: string;
}

interface Props {
  schedule: ScheduleEntry;
  onChange: (schedule: ScheduleEntry) => void;
  targetNewsletter: TargetNewsletter;
  validDates?: Set<string>;
  showRecurrenceControls?: boolean;
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
  const d = new Date(dateStr + 'T00:00:00');
  const day = d.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat

  if (target === 'myui' || target === 'both') {
    if (day !== 1) return 'My UI publishes on Mondays only.';
  } else if (target === 'tdr') {
    if (day === 0 || day === 6) return 'The Daily Register does not publish on weekends.';
  }
  return null;
}

function getMinDate(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow.toISOString().split('T')[0];
}

export default function SchedulePrefs({
  schedule,
  onChange,
  targetNewsletter,
  validDates,
  showRecurrenceControls = false,
}: Props) {
  const update = (field: keyof ScheduleEntry, value: string | number | boolean) => {
    onChange({ ...schedule, [field]: value });
  };

  const dateError = validateDate(schedule.Requested_Date, targetNewsletter, validDates);
  const recurrenceEndError = schedule.Recurrence_Type !== 'once'
    && schedule.Recurrence_End_Date
    && schedule.Recurrence_End_Date < schedule.Requested_Date
      ? 'End date cannot be before the first run date.'
      : null;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Scheduling Preferences
      </label>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">
            Preferred run date
          </label>
          <input
            type="date"
            value={schedule.Requested_Date}
            onChange={(e) => update('Requested_Date', e.target.value)}
            required
            min={getMinDate()}
            className={`w-full rounded-md border px-3 py-2 text-sm focus:ring-1 ${
              dateError
                ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-ui-gold-500 focus:ring-ui-gold-500'
            }`}
          />
          {dateError && (
            <p className="text-xs text-red-600 mt-1">{dateError}</p>
          )}
          <p className="text-xs text-gray-400 mt-1">
            {validDates
              ? 'Select a valid publication date'
              : targetNewsletter === 'myui' || targetNewsletter === 'both'
                ? 'My UI publishes Mondays only'
                : 'Mon–Fri only'}
          </p>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">
            How many times to run
          </label>
          <select
            value={schedule.Repeat_Count}
            onChange={(e) => update('Repeat_Count', parseInt(e.target.value))}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          >
            <option value={1}>Once</option>
            <option value={2}>Twice (has RSVP/registration)</option>
          </select>
        </div>
      </div>
      {showRecurrenceControls ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Repeat on a cadence
            </label>
            <select
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
            <p className="text-xs text-gray-400 mt-1">
              Use this for recurring items like every Friday or first Monday.
            </p>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Interval
            </label>
            <input
              type="number"
              min={1}
              max={12}
              value={schedule.Recurrence_Interval}
              onChange={(e) => update('Recurrence_Interval', parseInt(e.target.value, 10) || 1)}
              disabled={schedule.Recurrence_Type === 'once'}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
            <p className="text-xs text-gray-400 mt-1">
              {schedule.Recurrence_Type === 'weekly'
                ? 'Every N weeks'
                : schedule.Recurrence_Type === 'once'
                  ? 'Not used for one-time requests'
                  : 'Every N months'}
            </p>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Stop after
            </label>
            <input
              type="date"
              value={schedule.Recurrence_End_Date}
              onChange={(e) => update('Recurrence_End_Date', e.target.value)}
              disabled={schedule.Recurrence_Type === 'once'}
              min={schedule.Requested_Date || getMinDate()}
              className={`w-full rounded-md border px-3 py-2 text-sm focus:ring-1 disabled:bg-gray-50 disabled:text-gray-400 ${
                recurrenceEndError
                  ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 focus:border-ui-gold-500 focus:ring-ui-gold-500'
              }`}
            />
            {recurrenceEndError && (
              <p className="text-xs text-red-600 mt-1">{recurrenceEndError}</p>
            )}
            {!recurrenceEndError && (
              <p className="text-xs text-gray-400 mt-1">
                Optional. Leave blank to keep running.
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="mt-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
          <p className="text-xs text-gray-600">
            Recurring scheduling is managed by UCM staff after submission when needed.
          </p>
        </div>
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
            className="rounded border-gray-300 text-ui-gold-600 focus:ring-ui-gold-500"
          />
          My dates are somewhat flexible
        </label>
        {schedule.Is_Flexible && (
          <input
            type="text"
            placeholder="e.g., anytime the week of March 19"
            value={schedule.Flexible_Deadline}
            onChange={(e) => update('Flexible_Deadline', e.target.value)}
            className="mt-2 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          />
        )}
      </div>
      <div className="mt-3">
        <label className="block text-xs text-gray-500 mb-1">
          Scheduling notes (optional)
        </label>
        <input
          type="text"
          placeholder="e.g., 'Please skip finals week if needed'"
          value={schedule.Repeat_Note}
          onChange={(e) => update('Repeat_Note', e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
        />
      </div>
    </div>
  );
}
