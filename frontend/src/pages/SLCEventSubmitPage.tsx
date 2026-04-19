import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSubmission } from '../api/submissions';
import type { EventClassification } from '../types/submission';
import { getSubmitterRole } from '../utils/submitterRole';

type TicketedValue = '' | 'no' | 'yes' | 'eventbrite' | 'cvent';

const TICKETED_OPTIONS: { value: TicketedValue; label: string }[] = [
  { value: '', label: 'Not sure yet' },
  { value: 'no', label: 'No — open/free' },
  { value: 'yes', label: 'Yes — general ticketing' },
  { value: 'eventbrite', label: 'Yes — Eventbrite' },
  { value: 'cvent', label: 'Yes — CVENT' },
];

type ClassificationChoice = '' | EventClassification;

const CLASSIFICATION_OPTIONS: { value: ClassificationChoice; label: string; hint: string }[] = [
  { value: '', label: 'Not sure — let Aux Services decide', hint: '' },
  {
    value: 'strategic',
    label: 'Strategic',
    hint: 'Advances university priorities, relationships, operations, or institutional goals.',
  },
  {
    value: 'signature',
    label: 'Signature',
    hint: 'Highly visible, public-facing event that shapes campus or community perception.',
  },
];

function buildBody(fields: {
  eventName: string;
  location: string;
  sponsor: string;
  startTime: string;
  ticketedLabel: string;
  notes: string;
}): string {
  const parts = [`Event: ${fields.eventName}`];
  if (fields.location) parts.push(`Location: ${fields.location}`);
  if (fields.sponsor) parts.push(`Sponsor: ${fields.sponsor}`);
  if (fields.startTime) parts.push(`Start Time: ${fields.startTime}`);
  if (fields.ticketedLabel) parts.push(`Ticketed: ${fields.ticketedLabel}`);
  if (fields.notes) parts.push(`Notes: ${fields.notes}`);
  return parts.join('\n');
}

export default function SLCEventSubmitPage() {
  const navigate = useNavigate();
  const role = getSubmitterRole();
  const allowed = role === 'slc' || role === 'staff';

  const [submitterName, setSubmitterName] = useState('');
  const [submitterEmail, setSubmitterEmail] = useState('');
  const [eventName, setEventName] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [location, setLocation] = useState('');
  const [sponsor, setSponsor] = useState('');
  const [ticketed, setTicketed] = useState<TicketedValue>('');
  const [classification, setClassification] = useState<ClassificationChoice>('');
  const [notes, setNotes] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);

  if (!allowed) {
    return (
      <div className="max-w-2xl mx-auto mt-12 bg-white rounded-lg shadow p-8 text-center">
        <h2 className="text-lg font-semibold text-gray-900">Restricted</h2>
        <p className="mt-2 text-sm text-gray-600">
          SLC event submission is only available to SLC members, their admins,
          and UCM staff.
        </p>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!submitterName || !submitterEmail || !eventName || !eventDate) {
      setError('Submitter name, email, event name, and event date are required.');
      return;
    }

    const ticketedLabel =
      TICKETED_OPTIONS.find((opt) => opt.value === ticketed)?.label ?? '';

    const body = buildBody({
      eventName,
      location,
      sponsor,
      startTime,
      ticketedLabel: ticketed ? ticketedLabel : '',
      notes,
    });

    setSubmitting(true);
    try {
      const created = await createSubmission({
        Category: 'slc_event',
        Target_Newsletter: 'none',
        Original_Headline: eventName,
        Original_Body: body,
        Submitter_Name: submitterName,
        Submitter_Email: submitterEmail,
        Submitter_Notes: notes || undefined,
        Show_In_SLC_Calendar: true,
        Event_Classification: classification || undefined,
        Schedule_Requests: [
          {
            Requested_Date: eventDate,
            Recurrence_Type: 'once',
            Repeat_Count: 1,
          },
        ],
      });
      setSuccessId(created.Id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit event.');
    } finally {
      setSubmitting(false);
    }
  };

  if (successId) {
    return (
      <div className="max-w-2xl mx-auto mt-12 bg-white rounded-lg shadow p-8">
        <h2 className="text-lg font-semibold text-gray-900">Event submitted</h2>
        <p className="mt-3 text-sm text-gray-700">
          Thanks — your event has been sent to Auxiliary Services for review.
          You'll see it on the SLC calendar once it's approved.
        </p>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={() => navigate('/slc-calendar')}
            className="px-4 py-2 text-sm font-medium rounded-md bg-ui-gold-500 text-ui-black hover:bg-ui-gold-400"
          >
            View SLC Calendar
          </button>
          <button
            type="button"
            onClick={() => {
              setSuccessId(null);
              setEventName('');
              setEventDate('');
              setStartTime('');
              setLocation('');
              setSponsor('');
              setTicketed('');
              setClassification('');
              setNotes('');
            }}
            className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            Submit Another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Submit an SLC Calendar Event</h2>
        <p className="text-sm text-gray-500 mt-1">
          For Senior Leadership Council awareness. Submissions are reviewed by
          Auxiliary Services before appearing on the calendar.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow p-6 space-y-5"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Submitter Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={submitterName}
              onChange={(e) => setSubmitterName(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Submitter Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={submitterEmail}
              onChange={(e) => setSubmitterEmail(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Event Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={eventName}
            onChange={(e) => setEventName(e.target.value)}
            required
            maxLength={500}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Event Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={eventDate}
              onChange={(e) => setEventDate(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <p className="text-[11px] text-gray-400 mt-1">
              For multi-day events, use the start date and note the range in Notes.
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Start Time
            </label>
            <input
              type="text"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              placeholder="e.g. 5:30 PM"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Location
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. ICCU Arena"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Sponsor / Hosting Unit
            </label>
            <input
              type="text"
              value={sponsor}
              onChange={(e) => setSponsor(e.target.value)}
              placeholder="e.g. Alumni Relations"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Ticketed?
          </label>
          <select
            value={ticketed}
            onChange={(e) => setTicketed(e.target.value as TicketedValue)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {TICKETED_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Suggested Classification
          </label>
          <div className="space-y-2">
            {CLASSIFICATION_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className="flex items-start gap-3 rounded-md border border-gray-200 p-3 text-sm hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="radio"
                  name="classification"
                  value={opt.value}
                  checked={classification === opt.value}
                  onChange={(e) =>
                    setClassification(e.target.value as ClassificationChoice)
                  }
                  className="mt-0.5"
                />
                <div>
                  <div className="font-medium text-gray-900">{opt.label}</div>
                  {opt.hint && (
                    <div className="text-xs text-gray-500 mt-0.5">{opt.hint}</div>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Anything else SLC should know — date ranges, VIP guests, attendance expectations, etc."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate('/slc-calendar')}
            className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 text-sm font-medium rounded-md bg-ui-gold-500 text-ui-black hover:bg-ui-gold-400 disabled:opacity-50"
          >
            {submitting ? 'Submitting…' : 'Submit Event'}
          </button>
        </div>
      </form>
    </div>
  );
}
