interface ScheduleEntry {
  Requested_Date: string;
  Repeat_Count: number;
  Repeat_Note: string;
}

interface Props {
  schedule: ScheduleEntry;
  onChange: (schedule: ScheduleEntry) => void;
}

export default function SchedulePrefs({ schedule, onChange }: Props) {
  const update = (field: keyof ScheduleEntry, value: string | number) => {
    onChange({ ...schedule, [field]: value });
  };

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
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          />
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
