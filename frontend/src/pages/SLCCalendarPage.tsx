import { useEffect, useState, useCallback, useMemo } from 'react';
import { listSubmissions } from '../api/submissions';
import type { Submission, EventClassification } from '../types/submission';
import CalendarView from '../components/dashboard/CalendarView';
import DayDetail from '../components/dashboard/DayDetail';
import { getSubmitterRole } from '../utils/submitterRole';
import { getOccurrenceDates } from '../utils/submissionOccurrences';

const CLASSIFICATION_STYLES: Record<EventClassification, string> = {
  strategic: 'bg-ui-clearwater-50 text-ui-clearwater-700 border-ui-clearwater-200',
  signature: 'bg-ui-gold-50 text-ui-gold-700 border-ui-gold-200',
};

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default function SLCCalendarPage() {
  const role = getSubmitterRole();
  const allowed = role === 'slc' || role === 'staff';

  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentMonth, setCurrentMonth] = useState(() => new Date(2026, 3, 1));
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [classificationFilter, setClassificationFilter] = useState<'' | EventClassification>('');

  const fetchData = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    setError(null);
    try {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth();
      const data = await listSubmissions({
        slc_calendar_only: true,
        date_from: toISODate(new Date(year, month, 1)),
        date_to: toISODate(new Date(year, month + 1, 0)),
        limit: 200,
      });
      setSubmissions(data.Items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load SLC events');
    } finally {
      setLoading(false);
    }
  }, [currentMonth, allowed]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredSubmissions = useMemo(() => {
    if (!classificationFilter) return submissions;
    return submissions.filter((s) => s.Event_Classification === classificationFilter);
  }, [submissions, classificationFilter]);

  const eventsByDate = useMemo(() => {
    const map = new Map<string, Submission[]>();
    for (const sub of filteredSubmissions) {
      for (const dateKey of getOccurrenceDates(sub)) {
        if (!map.has(dateKey)) map.set(dateKey, []);
        map.get(dateKey)!.push(sub);
      }
    }
    return map;
  }, [filteredSubmissions]);

  if (!allowed) {
    return (
      <div className="max-w-2xl mx-auto mt-12 bg-white rounded-lg shadow p-8 text-center">
        <h2 className="text-lg font-semibold text-gray-900">Restricted calendar</h2>
        <p className="mt-2 text-sm text-gray-600">
          The Senior Leadership Council calendar is only available to authorized viewers.
          Switch to an SLC or Staff role from the landing page to view it.
        </p>
      </div>
    );
  }

  const totalsByClassification = filteredSubmissions.reduce(
    (acc, s) => {
      if (s.Event_Classification === 'signature') acc.signature += 1;
      else if (s.Event_Classification === 'strategic') acc.strategic += 1;
      else acc.unclassified += 1;
      return acc;
    },
    { signature: 0, strategic: 0, unclassified: 0 },
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Senior Leadership Council Calendar
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Strategic and signature events for leadership awareness.
            Access is limited to SLC members, their admins, and UCM staff.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded px-2 py-1 bg-ui-gold-50 text-ui-gold-700 border border-ui-gold-200">
            Signature: {totalsByClassification.signature}
          </span>
          <span className="rounded px-2 py-1 bg-ui-clearwater-50 text-ui-clearwater-700 border border-ui-clearwater-200">
            Strategic: {totalsByClassification.strategic}
          </span>
          <span className="rounded px-2 py-1 bg-gray-50 text-gray-600 border border-gray-200">
            Unclassified: {totalsByClassification.unclassified}
          </span>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Classification</label>
            <select
              value={classificationFilter}
              onChange={(e) =>
                setClassificationFilter(e.target.value as '' | EventClassification)
              }
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="strategic">Strategic only</option>
              <option value="signature">Signature only</option>
            </select>
          </div>
          <div className="text-xs text-gray-500 self-center">
            Showing {filteredSubmissions.length} event
            {filteredSubmissions.length === 1 ? '' : 's'} in{' '}
            {currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <CalendarView
              submissions={filteredSubmissions}
              selectedDate={selectedDate}
              onDateClick={setSelectedDate}
              currentMonth={currentMonth}
              onMonthChange={setCurrentMonth}
            />
          </div>
          <div>
            {selectedDate ? (
              <SLCDayPanel
                date={selectedDate}
                events={eventsByDate.get(selectedDate) ?? []}
              />
            ) : (
              <div className="bg-white rounded-lg shadow p-8 text-center">
                <p className="text-sm text-gray-400">
                  Click a date to see SLC events.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SLCDayPanel({ date, events }: { date: string; events: Submission[] }) {
  const display = new Date(date + 'T12:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">{display}</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          {events.length} event{events.length === 1 ? '' : 's'}
        </p>
      </div>
      <div className="p-4 space-y-3">
        {events.length === 0 && (
          <p className="text-sm text-gray-400">No SLC events on this date.</p>
        )}
        {events.map((event) => (
          <div
            key={event.Id}
            className="rounded-md border border-gray-200 p-3 text-sm"
          >
            <div className="flex items-start justify-between gap-2">
              <h4 className="font-medium text-gray-900">{event.Original_Headline}</h4>
              {event.Event_Classification && (
                <span
                  className={`shrink-0 text-[10px] uppercase tracking-wide rounded border px-1.5 py-0.5 ${
                    CLASSIFICATION_STYLES[event.Event_Classification]
                  }`}
                >
                  {event.Event_Classification}
                </span>
              )}
            </div>
            <pre className="mt-2 text-xs text-gray-600 whitespace-pre-wrap font-sans">
              {event.Original_Body}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
