import type { Submission } from '../../types/submission';

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const STATUS_DOT_COLORS: Record<string, string> = {
  new: 'bg-blue-400',
  ai_edited: 'bg-purple-400',
  in_review: 'bg-yellow-400',
  approved: 'bg-green-400',
  scheduled: 'bg-cyan-400',
  published: 'bg-gray-400',
  rejected: 'bg-red-400',
};

interface CalendarViewProps {
  submissions: Submission[];
  selectedDate: string | null;
  onDateClick: (date: string) => void;
  currentMonth: Date;
  onMonthChange: (date: Date) => void;
}

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getSubmissionsByDate(submissions: Submission[]): Map<string, Submission[]> {
  const map = new Map<string, Submission[]>();
  for (const sub of submissions) {
    for (const sched of sub.Schedule_Requests) {
      if (sched.Requested_Date) {
        const dateKey = sched.Requested_Date;
        if (!map.has(dateKey)) map.set(dateKey, []);
        map.get(dateKey)!.push(sub);
      }
    }
  }
  return map;
}

export default function CalendarView({
  submissions,
  selectedDate,
  onDateClick,
  currentMonth,
  onMonthChange,
}: CalendarViewProps) {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startOffset = firstDay.getDay();
  const daysInMonth = lastDay.getDate();

  const today = toISODate(new Date());
  const submissionsByDate = getSubmissionsByDate(submissions);

  const prevMonth = () => onMonthChange(new Date(year, month - 1, 1));
  const nextMonth = () => onMonthChange(new Date(year, month + 1, 1));

  const monthLabel = currentMonth.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  // Build grid cells
  const cells: (number | null)[] = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Month navigation */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <button
          onClick={prevMonth}
          className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded"
        >
          &#x25C0;
        </button>
        <h3 className="text-sm font-semibold text-gray-900">{monthLabel}</h3>
        <button
          onClick={nextMonth}
          className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded"
        >
          &#x25B6;
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 border-b border-gray-100">
        {DAYS_OF_WEEK.map((day) => (
          <div
            key={day}
            className="py-2 text-center text-xs font-medium text-gray-500"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7">
        {cells.map((day, idx) => {
          if (day === null) {
            return <div key={`empty-${idx}`} className="h-20 border-b border-r border-gray-50" />;
          }

          const dateStr = toISODate(new Date(year, month, day));
          const daySubs = submissionsByDate.get(dateStr) || [];
          const isToday = dateStr === today;
          const isSelected = dateStr === selectedDate;

          return (
            <button
              key={dateStr}
              onClick={() => onDateClick(dateStr)}
              className={`h-20 border-b border-r border-gray-50 p-1 text-left hover:bg-gray-50 transition-colors ${
                isSelected ? 'bg-ui-gold-50 ring-1 ring-ui-gold-300' : ''
              } ${isToday && !isSelected ? 'bg-blue-50' : ''}`}
            >
              <span
                className={`text-xs font-medium ${
                  isToday
                    ? 'bg-ui-gold-500 text-white rounded-full w-5 h-5 inline-flex items-center justify-center'
                    : 'text-gray-700'
                }`}
              >
                {day}
              </span>
              {daySubs.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-0.5">
                  {daySubs.length <= 4 ? (
                    daySubs.map((sub) => (
                      <span
                        key={sub.Id}
                        className={`w-2 h-2 rounded-full ${STATUS_DOT_COLORS[sub.Status] || 'bg-gray-400'}`}
                        title={sub.Original_Headline}
                      />
                    ))
                  ) : (
                    <span className="text-xs font-medium text-ui-gold-700 bg-ui-gold-50 px-1 rounded">
                      {daySubs.length}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
