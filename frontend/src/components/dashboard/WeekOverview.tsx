import type { Submission } from '../../types/submission';
import { getOccurrenceDates } from '../../utils/submissionOccurrences';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

interface WeekOverviewProps {
  submissions: Submission[];
  weekStart: string;
  selectedDate: string | null;
  onDateClick: (date: string) => void;
  validDates?: Map<string, string[]>;
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T12:00:00');
  d.setDate(d.getDate() + days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getMonday(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
}

export default function WeekOverview({
  submissions,
  weekStart,
  selectedDate,
  onDateClick,
  validDates,
}: WeekOverviewProps) {
  const monday = getMonday(weekStart);
  const weekDates = DAY_LABELS.map((_, i) => addDays(monday, i));

  // Count submissions per day
  const countsByDate = new Map<string, { tdr: number; myui: number; total: number }>();
  for (const dateStr of weekDates) {
    countsByDate.set(dateStr, { tdr: 0, myui: 0, total: 0 });
  }

  for (const sub of submissions) {
    const occDates = getOccurrenceDates(sub);
    for (const dateStr of weekDates) {
      if (occDates.includes(dateStr)) {
        const counts = countsByDate.get(dateStr)!;
        counts.total++;
        if (sub.Target_Newsletter === 'tdr' || sub.Target_Newsletter === 'both') counts.tdr++;
        if (sub.Target_Newsletter === 'myui' || sub.Target_Newsletter === 'both') counts.myui++;
      }
    }
  }

  const maxCount = Math.max(1, ...Array.from(countsByDate.values()).map((c) => c.total));

  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  const weekLabel = (() => {
    const start = new Date(monday + 'T12:00:00');
    const end = new Date(addDays(monday, 4) + 'T12:00:00');
    const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
    return `${start.toLocaleDateString('en-US', opts)} — ${end.toLocaleDateString('en-US', opts)}`;
  })();

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900">Week Overview</h3>
        <span className="text-xs text-gray-500">{weekLabel}</span>
      </div>

      <div className="grid grid-cols-5 gap-2">
        {weekDates.map((dateStr, idx) => {
          const counts = countsByDate.get(dateStr)!;
          const isToday = dateStr === todayStr;
          const isSelected = dateStr === selectedDate;
          const pubNewsletters = validDates?.get(dateStr);
          const isPubDay = !!pubNewsletters && pubNewsletters.length > 0;
          const barHeight = Math.max(4, (counts.total / maxCount) * 48);

          return (
            <button
              key={dateStr}
              onClick={() => onDateClick(dateStr)}
              className={`flex flex-col items-center rounded-lg p-2 transition-colors ${
                isSelected
                  ? 'bg-ui-gold-50 ring-1 ring-ui-gold-300'
                  : isToday
                    ? 'bg-blue-50'
                    : 'hover:bg-gray-50'
              }`}
            >
              <span className={`text-xs font-medium ${isToday ? 'text-ui-gold-700' : 'text-gray-500'}`}>
                {DAY_LABELS[idx]}
              </span>
              <span className={`text-xs ${isToday ? 'text-ui-gold-600 font-semibold' : 'text-gray-400'}`}>
                {new Date(dateStr + 'T12:00:00').getDate()}
              </span>

              {/* Bar */}
              <div className="w-full flex justify-center items-end h-12 mt-1">
                {isPubDay ? (
                  <div
                    className="w-6 rounded-t flex flex-col justify-end overflow-hidden"
                    style={{ height: `${barHeight}px` }}
                  >
                    {counts.tdr > 0 && (
                      <div
                        className="w-full bg-ui-gold-400"
                        style={{
                          height: `${(counts.tdr / counts.total) * 100}%`,
                          minHeight: counts.tdr > 0 ? '2px' : '0',
                        }}
                      />
                    )}
                    {counts.myui > 0 && (
                      <div
                        className="w-full bg-blue-400"
                        style={{
                          height: `${(counts.myui / counts.total) * 100}%`,
                          minHeight: counts.myui > 0 ? '2px' : '0',
                        }}
                      />
                    )}
                    {counts.total === 0 && (
                      <div className="w-full bg-gray-200 h-1 rounded" />
                    )}
                  </div>
                ) : (
                  <div className="w-6 h-1 bg-gray-100 rounded" />
                )}
              </div>

              {/* Count */}
              <span className={`text-xs font-bold mt-1 ${
                counts.total === 0
                  ? 'text-gray-300'
                  : counts.total >= 8
                    ? 'text-red-600'
                    : counts.total >= 5
                      ? 'text-amber-600'
                      : 'text-gray-700'
              }`}>
                {counts.total}
              </span>
            </button>
          );
        })}
      </div>

      {/* Load indicators */}
      <div className="mt-2 flex items-center justify-center gap-4 text-[10px] text-gray-400">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-sm bg-ui-gold-400" /> TDR
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-sm bg-blue-400" /> My UI
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-red-600 opacity-50" /> Heavy
        </span>
      </div>
    </div>
  );
}
