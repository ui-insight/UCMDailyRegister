import { useState } from 'react';
import type { SubmissionScheduleRequest } from '../../types/submission';

/** How a repeating schedule ends: on a date, or never (staff only, #538). */
export interface ScheduleEnding {
  Recurrence_End_Date?: string;
  Repeats_Indefinitely?: boolean;
}

interface ScheduleEndingEditorProps {
  request: SubmissionScheduleRequest;
  onSave: (ending: ScheduleEnding) => Promise<void>;
  onClose: () => void;
}

/**
 * Inline staff form to end a repeating series on a date or set it to repeat
 * indefinitely. Only the ending changes; dates already published stay.
 */
export default function ScheduleEndingEditor({ request, onSave, onClose }: ScheduleEndingEditorProps) {
  const [endDate, setEndDate] = useState(request.Recurrence_End_Date ?? '');
  const [indefinite, setIndefinite] = useState(request.Repeats_Indefinitely);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const startDate = request.Requested_Date || request.Second_Requested_Date;
  const inputId = `schedule-ending-${request.Id}`;

  const handleSave = async () => {
    if (!indefinite && !endDate) {
      setError('Choose the last run date, or tick Repeat indefinitely.');
      return;
    }
    if (!indefinite && startDate && endDate < startDate) {
      setError('The end date cannot be before the first run date.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onSave(indefinite ? { Repeats_Indefinitely: true } : { Recurrence_End_Date: endDate });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save the end date');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-2 rounded-md border border-ui-gold-200 bg-ui-gold-50 p-2 space-y-2 font-normal">
      <label className="flex items-center gap-2 text-xs text-gray-700">
        <input
          type="checkbox"
          checked={indefinite}
          onChange={(e) => {
            setIndefinite(e.target.checked);
            if (e.target.checked) setEndDate('');
            setError('');
          }}
          className="rounded border-gray-300 text-ui-gold-800 focus:ring-ui-gold-500"
        />
        Repeat indefinitely
      </label>
      {!indefinite && (
        <div>
          <label htmlFor={inputId} className="block text-[10px] text-gray-500 mb-0.5">
            Last run date
          </label>
          <input
            id={inputId}
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(e) => { setEndDate(e.target.value); setError(''); }}
            className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          />
          <div className="mt-1 text-[10px] text-gray-600">
            Dates already published stay in their newsletters.
          </div>
        </div>
      )}
      {error && <div className="text-[10px] text-status-error-800">{error}</div>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="text-xs rounded bg-ui-gold-500 px-3 py-1 text-ui-black hover:bg-ui-gold-600 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save ending'}
        </button>
        <button
          type="button"
          onClick={onClose}
          disabled={saving}
          className="text-xs rounded border border-gray-300 px-3 py-1 text-gray-600 hover:bg-white disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
