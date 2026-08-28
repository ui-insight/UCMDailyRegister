import { useEffect, useState, useCallback, useMemo } from 'react';
import { listHarvestedEvents, runHarvest, updateHarvestedEvent } from '../api/slcEvents';
import type { HarvestedEvent, SLCReviewStatus } from '../types/harvestedEvent';
import { getSubmitterRole } from '../utils/submitterRole';
import { EmptyState } from '../components/common';
import { toISODate } from '../utils/date';

const LOOKAHEAD_DAYS = 60;

type Classification = 'strategic' | 'signature';
type StatusFilter = '' | SLCReviewStatus;

function matchesStatusFilter(event: HarvestedEvent, filter: StatusFilter): boolean {
  if (!filter) return event.SLC_Review_Status !== 'dismissed';
  return event.SLC_Review_Status === filter;
}

function topCategory(event: HarvestedEvent): string {
  return event.Category_Path?.split('|')[0] ?? 'Uncategorized';
}

function weekStartKey(isoDateTime: string): string {
  const d = new Date(isoDateTime);
  const daysSinceMonday = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - daysSinceMonday);
  return toISODate(d);
}

function formatWeekHeading(weekStartISO: string): string {
  return `Week of ${new Date(weekStartISO + 'T12:00:00').toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })}`;
}

function formatEventDate(event: HarvestedEvent): string {
  return new Date(event.Event_Start).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

function formatEventTime(event: HarvestedEvent): string {
  if (event.All_Day) return 'All day';
  const timeOptions: Intl.DateTimeFormatOptions = { hour: 'numeric', minute: '2-digit' };
  const start = new Date(event.Event_Start).toLocaleTimeString('en-US', timeOptions);
  if (!event.Event_End) return start;
  const end = new Date(event.Event_End).toLocaleTimeString('en-US', timeOptions);
  return `${start} – ${end}`;
}

export default function SLCTriagePage() {
  const role = getSubmitterRole();
  const allowed = role === 'slc' || role === 'staff';

  const [events, setEvents] = useState<HarvestedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [harvesting, setHarvesting] = useState(false);
  const [harvestSummary, setHarvestSummary] = useState<string | null>(null);
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
      const data = await listHarvestedEvents({
        date_from: toISODate(today),
        date_to: toISODate(horizon),
        review_status: statusFilter || undefined,
        limit: 500,
      });
      setEvents(data.Items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load harvested events');
    } finally {
      setLoading(false);
    }
  }, [allowed, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = async () => {
    setHarvesting(true);
    setError(null);
    setHarvestSummary(null);
    try {
      const summary = await runHarvest();
      setHarvestSummary(
        `Feed refreshed: ${summary.Created} new, ${summary.Updated} updated, `
        + `${summary.Unchanged} unchanged.`,
      );
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh the events feed');
    } finally {
      setHarvesting(false);
    }
  };

  const handleTriage = async (
    event: HarvestedEvent,
    status: SLCReviewStatus,
    classification?: Classification,
  ) => {
    setBusyEventId(event.Id);
    setError(null);
    try {
      const updated = await updateHarvestedEvent(event.Id, {
        SLC_Review_Status: status,
        ...(classification ? { Event_Classification: classification } : {}),
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
    const map = new Map<string, HarvestedEvent[]>();
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
          SLC event triage is only available to authorized viewers. Switch to an
          SLC or Staff role from the landing page to view it.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">SLC Event Triage</h2>
          <p className="text-sm text-gray-500 mt-1">
            Upcoming campus events harvested from the U of I events calendar.
            Review them for Senior Leadership Council relevance.
          </p>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={harvesting}
          className="rounded-md bg-ui-gold-500 px-4 py-2 text-sm font-medium text-ui-black hover:bg-ui-gold-400 disabled:opacity-50"
        >
          {harvesting ? 'Refreshing…' : 'Refresh events'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label htmlFor="slc-triage-category" className="block text-xs text-gray-500 mb-1">
              Category
            </label>
            <select
              id="slc-triage-category"
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
            <label htmlFor="slc-triage-status" className="block text-xs text-gray-500 mb-1">
              Status
            </label>
            <select
              id="slc-triage-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Active (new + flagged)</option>
              <option value="new">New only</option>
              <option value="flagged">Flagged only</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>
          <div className="text-xs text-gray-500 self-center">
            Showing {filteredEvents.length} event
            {filteredEvents.length === 1 ? '' : 's'} over the next {LOOKAHEAD_DAYS} days
          </div>
        </div>
        {harvestSummary && (
          <p className="mt-3 text-xs text-ui-clearwater-700">{harvestSummary}</p>
        )}
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
          title="No harvested events yet"
          description='Use "Refresh events" to pull the latest events from the university calendar feed.'
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
                  <TriageEventCard
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

function TriageEventCard({
  event,
  busy,
  onTriage,
}: {
  event: HarvestedEvent;
  busy: boolean;
  onTriage: (
    event: HarvestedEvent,
    status: SLCReviewStatus,
    classification?: Classification,
  ) => void;
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
            {event.SLC_Review_Status === 'flagged' && (
              <span className="text-[10px] uppercase tracking-wide rounded border border-ui-clearwater-200 bg-ui-clearwater-50 px-1.5 py-0.5 text-ui-clearwater-700">
                Flagged{event.Promoted_Classification ? `: ${event.Promoted_Classification}` : ''}
              </span>
            )}
            {event.SLC_Review_Status === 'dismissed' && (
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
            <TriageActions event={event} busy={busy} onTriage={onTriage} />
          </div>
        </div>
      </div>
    </div>
  );
}

function TriageActions({
  event,
  busy,
  onTriage,
}: {
  event: HarvestedEvent;
  busy: boolean;
  onTriage: (
    event: HarvestedEvent,
    status: SLCReviewStatus,
    classification?: Classification,
  ) => void;
}) {
  const buttonClass =
    'rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50';

  if (event.SLC_Review_Status === 'new') {
    return (
      <>
        <select
          aria-label={`Flag ${event.Title} for SLC`}
          value=""
          disabled={busy}
          onChange={(e) => {
            const value = e.target.value;
            if (!value) return;
            onTriage(
              event,
              'flagged',
              value === 'unclassified' ? undefined : (value as Classification),
            );
          }}
          className="rounded-md border border-ui-gold-400 bg-ui-gold-50 px-2.5 py-1 text-xs font-medium text-ui-black disabled:opacity-50"
        >
          <option value="">Flag for SLC…</option>
          <option value="unclassified">Flag (unclassified)</option>
          <option value="strategic">Flag as strategic</option>
          <option value="signature">Flag as signature</option>
        </select>
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

  if (event.SLC_Review_Status === 'flagged') {
    return (
      <>
        <select
          aria-label={`Classification for ${event.Title}`}
          value={event.Promoted_Classification ?? 'unclassified'}
          disabled={busy}
          onChange={(e) => {
            const value = e.target.value;
            onTriage(
              event,
              'flagged',
              value === 'unclassified' ? undefined : (value as Classification),
            );
          }}
          className="rounded-md border border-gray-300 px-2.5 py-1 text-xs text-gray-700 disabled:opacity-50"
        >
          <option value="unclassified">Unclassified</option>
          <option value="strategic">Strategic</option>
          <option value="signature">Signature</option>
        </select>
        <button
          type="button"
          disabled={busy}
          onClick={() => onTriage(event, 'new')}
          className={buttonClass}
        >
          Un-flag
        </button>
      </>
    );
  }

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
