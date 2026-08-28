import { useCallback, useEffect, useMemo, useState } from 'react';
import { listSubmissions } from '../api/submissions';
import type { EventClassification, Submission } from '../types/submission';
import { getSubmitterRole } from '../utils/submitterRole';
import { EmptyState, Toast, useToast } from '../components/common';
import { addDaysToISODate } from '../utils/date';
import { copyHtmlToClipboard } from '../utils/clipboard';
import {
  buildDefaultPreamble,
  buildDigestDays,
  buildDigestHtml,
  buildDigestText,
  defaultDigestWeekStart,
  formatDayHeading,
  formatWeekRange,
  truncateDescription,
  weekStartOf,
  type DigestEvent,
} from '../utils/slcDigest';

const CLASSIFICATION_STYLES: Record<EventClassification, string> = {
  strategic: 'bg-ui-clearwater-50 text-ui-clearwater-700 border-ui-clearwater-200',
  signature: 'bg-ui-gold-50 text-ui-gold-700 border-ui-gold-200',
};

export default function SLCDigestPage() {
  const role = getSubmitterRole();
  const allowed = role === 'slc' || role === 'staff';

  const [weekStart, setWeekStart] = useState(() => defaultDigestWeekStart());
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copying, setCopying] = useState(false);
  const { toast, showToast, dismissToast } = useToast();

  const fetchData = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listSubmissions({
        slc_calendar_only: true,
        date_from: weekStart,
        date_to: addDaysToISODate(weekStart, 6),
        limit: 200,
      });
      setSubmissions(data.Items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load SLC events');
    } finally {
      setLoading(false);
    }
  }, [allowed, weekStart]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const days = useMemo(
    () => buildDigestDays(submissions, weekStart),
    [submissions, weekStart],
  );
  const eventCount = new Set(
    days.flatMap((day) => day.events.map((event) => event.submission.Id)),
  ).size;

  const suggestedPreamble = useMemo(
    () => buildDefaultPreamble(weekStart, days),
    [weekStart, days],
  );
  const [preambleDraft, setPreambleDraft] = useState<string | null>(null);
  const preamble = preambleDraft ?? suggestedPreamble;

  const handleCopy = async () => {
    setCopying(true);
    setError(null);
    try {
      const flavor = await copyHtmlToClipboard(
        buildDigestHtml(weekStart, days, preamble),
        buildDigestText(weekStart, days, preamble),
      );
      showToast(
        flavor === 'rich'
          ? 'Copied — paste into your Outlook email'
          : 'Copied as plain text (this browser cannot copy formatting)',
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to copy the digest');
    } finally {
      setCopying(false);
    }
  };

  if (!allowed) {
    return (
      <div className="max-w-2xl mx-auto mt-12 bg-white rounded-lg shadow p-8 text-center">
        <h2 className="text-lg font-semibold text-gray-900">Restricted page</h2>
        <p className="mt-2 text-sm text-gray-600">
          The weekly SLC digest is only available to authorized viewers. Switch
          to an SLC or Staff role from the landing page to view it.
        </p>
      </div>
    );
  }

  const thisWeek = weekStartOf(new Date());
  const nextWeek = defaultDigestWeekStart();
  const weekButtonClass = (active: boolean) =>
    `rounded-md border px-3 py-1.5 text-xs font-medium ${
      active
        ? 'border-ui-gold-400 bg-ui-gold-50 text-ui-black'
        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
    }`;

  return (
    <div>
      <Toast toast={toast} onDismiss={dismissToast} />
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Weekly SLC Digest</h2>
          <p className="text-sm text-gray-500 mt-1">
            Flagged and submitted SLC events for one week, formatted for the
            weekly leadership email. Copy it, then paste into Outlook.
          </p>
        </div>
        <button
          type="button"
          onClick={handleCopy}
          disabled={copying || loading || eventCount === 0}
          className="rounded-md bg-ui-gold-500 px-4 py-2 text-sm font-medium text-ui-black hover:bg-ui-gold-400 disabled:opacity-50"
        >
          {copying ? 'Copying…' : 'Copy for email'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center gap-3 flex-wrap">
          <button
            type="button"
            aria-label="Previous week"
            onClick={() => setWeekStart((current) => addDaysToISODate(current, -7))}
            className="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            ‹
          </button>
          <span className="text-sm font-medium text-gray-900 min-w-52 text-center">
            {formatWeekRange(weekStart)}
          </span>
          <button
            type="button"
            aria-label="Next week"
            onClick={() => setWeekStart((current) => addDaysToISODate(current, 7))}
            className="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            ›
          </button>
          <div className="flex items-center gap-2 ml-2">
            <button
              type="button"
              onClick={() => setWeekStart(thisWeek)}
              className={weekButtonClass(weekStart === thisWeek)}
            >
              This week
            </button>
            <button
              type="button"
              onClick={() => setWeekStart(nextWeek)}
              className={weekButtonClass(weekStart === nextWeek)}
            >
              Next week
            </button>
          </div>
          <div className="text-xs text-gray-500 ml-auto">
            {loading
              ? 'Loading…'
              : `${eventCount} event${eventCount === 1 ? '' : 's'} this week`}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center justify-between gap-3 mb-2">
          <label
            htmlFor="slc-digest-preamble"
            className="text-sm font-medium text-gray-900"
          >
            Email preamble
          </label>
          {preambleDraft !== null && (
            <button
              type="button"
              onClick={() => setPreambleDraft(null)}
              className="text-xs font-medium text-ui-clearwater-700 hover:text-ui-clearwater-600"
            >
              Reset to suggested text
            </button>
          )}
        </div>
        <textarea
          id="slc-digest-preamble"
          value={preamble}
          onChange={(e) => setPreambleDraft(e.target.value)}
          rows={4}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900"
        />
        <p className="mt-1 text-xs text-gray-500">
          Included at the top of the copied email. The suggested text updates
          with the selected week until you edit it.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : days.length === 0 ? (
        <EmptyState
          title="No SLC events this week"
          description="Events flagged on the SLC Triage page or submitted to the SLC calendar will appear here when they fall in the selected week."
        />
      ) : (
        <div className="bg-white rounded-lg shadow p-6 max-w-3xl">
          <h3 className="text-lg font-bold text-gray-900">
            Senior Leadership Council Events
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            Week of {formatWeekRange(weekStart)}
          </p>
          {preamble
            .split(/\n{2,}/)
            .filter((paragraph) => paragraph.trim())
            .map((paragraph, index) => (
              <p
                key={index}
                className="text-sm text-gray-700 mb-3 whitespace-pre-line"
              >
                {paragraph.trim()}
              </p>
            ))}
          {days.map((day) => (
            <section key={day.date} className="mt-5 first:mt-0">
              <h4 className="text-sm font-semibold text-ui-clearwater-700 border-b border-gray-100 pb-1 mb-2">
                {formatDayHeading(day.date)}
              </h4>
              <div className="space-y-3">
                {day.events.map((event) => (
                  <DigestEventRow
                    key={`${day.date}-${event.submission.Id}`}
                    event={event}
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

function DigestEventRow({ event }: { event: DigestEvent }) {
  const detail = [
    event.time,
    event.location,
    event.sponsor,
    event.category,
    event.ticketed ? `Ticketed: ${event.ticketed}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
  return (
    <div className="text-sm">
      <div className="flex items-center gap-2">
        {event.url ? (
          <a
            href={event.url}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-ui-clearwater-700 hover:text-ui-clearwater-600 underline decoration-ui-clearwater-200"
          >
            {event.submission.Original_Headline}
          </a>
        ) : (
          <span className="font-medium text-gray-900">
            {event.submission.Original_Headline}
          </span>
        )}
        {event.classification && (
          <span
            className={`shrink-0 text-[10px] uppercase tracking-wide rounded border px-1.5 py-0.5 ${
              CLASSIFICATION_STYLES[event.classification]
            }`}
          >
            {event.classification}
          </span>
        )}
      </div>
      {detail && <p className="text-xs text-gray-500 mt-0.5">{detail}</p>}
      {event.description && (
        <p className="text-xs text-gray-600 mt-0.5">
          {truncateDescription(event.description)}
        </p>
      )}
    </div>
  );
}
