import type { TargetNewsletter } from '../../types/submission';

interface ScheduleEntry {
  Requested_Date: string;
  Repeat_Count: number;
  Repeat_Note: string;
  Is_Flexible: boolean;
  Flexible_Deadline: string;
}

interface Props {
  schedule: ScheduleEntry;
  onChange: (schedule: ScheduleEntry) => void;
  targetNewsletter: TargetNewsletter;
}

function validateDate(dateStr: string, target: TargetNewsletter): string | null {
  if (!dateStr) return null;
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

export default function SchedulePrefs({ schedule, onChange, targetNewsletter }: Props) {
  const update = (field: keyof ScheduleEntry, value: string | number | boolean) => {
    onChange({ ...schedule, [field]: value });
  };

  const dateError = validateDate(schedule.Requested_Date, targetNewsletter);

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
            {targetNewsletter === 'myui' || targetNewsletter === 'both'
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
      <div className="mt-3">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={schedule.Is_Flexible}
            onChange={(e) => {
              update('Is_Flexible', e.target.checked);
              if (!e.target.checked) update('Flexible_Deadline', '');
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
          placeholder="e.g., 'Please run on April 3 and again on April 10'"
          value={schedule.Repeat_Note}
          onChange={(e) => update('Repeat_Note', e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
        />
      </div>
    </div>
  );
}
