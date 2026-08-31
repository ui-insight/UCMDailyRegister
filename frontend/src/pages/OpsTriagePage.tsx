import { useEffect, useState, useCallback, useMemo } from 'react';
import { listOpsEvents, updateOpsEvent } from '../api/opsEvents';
import type { OpsEvent, OpsReviewStatus } from '../types/harvestedEvent';
import { getSubmitterRole } from '../utils/submitterRole';
import { EmptyState } from '../components/common';
import { toISODate } from '../utils/date';
import {
  formatEventDate,
  formatEventTime,
  formatWeekHeading,
  topCategory,
  weekStartKey,
} from '../utils/eventDisplay';

const LOOKAHEAD_DAYS = 60;

type StatusFilter = '' | OpsReviewStatus;

function matchesStatusFilter(event: OpsEvent, filter: StatusFilter): boolean {
  if (!filter) return event.Ops_Review_Status !== 'dismissed';
  return event.Ops_Review_Status === filter;
}

export default function OpsTriagePage() {
  const role = getSubmitterRole();
  const allowed = role === 'ops' || role === 'staff';

  const [events, setEvents] = useState<OpsEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const [busyEventId, setBusyEventId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    setError(null);
    try {
      const today = new Date();
      const horizon = new Date();
      horizon.setDate(today.getDate() + LOOKAHEAD_DAYS);
      const data = await listOpsEvents({
        date_from: toISODate(today),
        date_to: toISODate(horizon),
        review_status: statusFilter || undefined,
        limit: 500,
      });
      setEvents(data.Items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load events');
    } finally {
      setLoading(false);
    }
  }, [allowed, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleTriage = async (event: OpsEvent, status: OpsReviewStatus) => {
    setBusyEventId(event.Id);
    setError(null);
    try {
      const updated = await updateOpsEvent(event.Id, {
        Ops_Review_Status: status,
      });
      setEvents((current) =>
        current.map((item) => (item.Id === updated.Id ? updated : item)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update the event');
    } finally {
      setBusyEventId(null);
    }
  };

  const categories = useMemo(() => {
    const unique = new Set(events.map(topCategory));
    return [...unique].sort((a, b) => a.localeCompare(b));
  }, [events]);

  const filteredEvents = useMemo(() => {
    return events.filter(
      (event) =>
        matchesStatusFilter(event, statusFilter)
        && (!categoryFilter || topCategory(event) === categoryFilter),
    );
  }, [events, categoryFilter, statusFilter]);

  const eventsByWeek = useMemo(() => {
    const map = new Map<string, OpsEvent[]>();
    for (const event of filteredEvents) {
      const key = weekStartKey(event.Event_Start);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(event);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [filteredEvents]);

  if (!allowed) {
    return (
      <div className="max-w-2xl mx-auto mt-12 bg-white rounded-lg shadow p-8 text-center">
        <h2 className="text-lg font-semibold text-gray-900">Restricted page</h2>
        <p className="mt-2 text-sm text-gray-600">
          Ops event triage is only available to Event Services and staff.
          Switch to an Event Services or Staff role from the landing page to
          view it.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Ops Event Triage</h2>
        <p className="text-sm text-gray-500 mt-1">
          Upcoming campus events harvested from the U of I events calendar.
          Watch for events that may need Event Services support — catering,
          alcohol service, room setup, tabling, or outdoor space.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label htmlFor="ops-triage-category" className="block text-xs text-gray-500 mb-1">
              Category
            </label>
            <select
              id="ops-triage-category"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All categories</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="ops-triage-status" className="block text-xs text-gray-500 mb-1">
              Status
            </label>
            <select
              id="ops-triage-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Active (new + reviewed)</option>
              <option value="new">New only</option>
              <option value="reviewed">Reviewed only</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>
          <div className="text-xs text-gray-500 self-center">
            Showing {filteredEvents.length} event
            {filteredEvents.length === 1 ? '' : 's'} over the next {LOOKAHEAD_DAYS} days
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
      ) : eventsByWeek.length === 0 ? (
        <EmptyState
          title="No upcoming events"
          description="Harvested events will appear here after the next scheduled harvest of the university calendar feed."
        />
      ) : (
        <div className="space-y-8">
          {eventsByWeek.map(([weekStart, weekEvents]) => (
            <section key={weekStart}>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
                {formatWeekHeading(weekStart)}
              </h3>
              <div className="space-y-3">
                {weekEvents.map((event) => (
                  <OpsEventCard
                    key={event.Id}
                    event={event}
                    busy={busyEventId === event.Id}
                    onTriage={handleTriage}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function OpsEventCard({
  event,
  busy,
  onTriage,
}: {
  event: OpsEvent;
  busy: boolean;
  onTriage: (event: OpsEvent, status: OpsReviewStatus) => void;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4 flex gap-4">
      <div className="w-28 shrink-0 text-sm">
        <div className="font-medium text-gray-900">{formatEventDate(event)}</div>
        <div className="text-xs text-gray-500 mt-0.5">{formatEventTime(event)}</div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h4
            className={`font-medium ${
              event.Is_Canceled ? 'text-gray-400 line-through' : 'text-gray-900'
            }`}
          >
            {event.Title}
          </h4>
          <div className="flex shrink-0 items-center gap-1.5">
            {event.Is_Canceled && (
              <span className="text-[10px] uppercase tracking-wide rounded border border-red-200 bg-red-50 px-1.5 py-0.5 text-red-700">
                Canceled
              </span>
            )}
            {event.Ops_Review_Status === 'reviewed' && (
              <span className="text-[10px] uppercase tracking-wide rounded border border-ui-clearwater-200 bg-ui-clearwater-50 px-1.5 py-0.5 text-ui-clearwater-700">
                Reviewed
              </span>
            )}
            {event.Ops_Review_Status === 'dismissed' && (
              <span className="text-[10px] uppercase tracking-wide rounded border border-gray-200 bg-gray-100 px-1.5 py-0.5 text-gray-500">
                Dismissed
              </span>
            )}
            <span className="text-[10px] uppercase tracking-wide rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-gray-600">
              {topCategory(event)}
            </span>
          </div>
        </div>
        {event.Location && (
          <p className="text-xs text-gray-500 mt-0.5">{event.Location}</p>
        )}
        {event.Description && (
          <p className="text-xs text-gray-600 mt-1.5 line-clamp-2">{event.Description}</p>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {event.Source_Url && (
            <a
              href={event.Source_Url}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-medium text-ui-clearwater-700 hover:text-ui-clearwater-600"
            >
              Event page ↗
            </a>
          )}
          <div className="ml-auto flex items-center gap-2">
            <OpsTriageActions event={event} busy={busy} onTriage={onTriage} />
          </div>
        </div>
      </div>
    </div>
  );
}

function OpsTriageActions({
  event,
  busy,
  onTriage,
}: {
  event: OpsEvent;
  busy: boolean;
  onTriage: (event: OpsEvent, status: OpsReviewStatus) => void;
}) {
  const buttonClass =
    'rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50';

  if (event.Ops_Review_Status === 'dismissed') {
    return (
      <button
        type="button"
        disabled={busy}
        onClick={() => onTriage(event, 'new')}
        className={buttonClass}
      >
        Restore
      </button>
    );
  }

  const reviewed = event.Ops_Review_Status === 'reviewed';
  return (
    <>
      <label
        className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium ${
          reviewed
            ? 'border-ui-gold-400 bg-ui-gold-50 text-ui-black'
            : 'border-gray-300 text-gray-700 hover:bg-gray-50'
        } ${busy ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
      >
        <input
          type="checkbox"
          aria-label={`Mark ${event.Title} reviewed`}
          checked={reviewed}
          disabled={busy}
          onChange={() => onTriage(event, reviewed ? 'new' : 'reviewed')}
          className="h-3.5 w-3.5 accent-ui-gold-500"
        />
        Reviewed
      </label>
      <button
        type="button"
        disabled={busy}
        onClick={() => onTriage(event, 'dismissed')}
        className={buttonClass}
      >
        Dismiss
      </button>
    </>
  );
}
