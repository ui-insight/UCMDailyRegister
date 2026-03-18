import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listSubmissions } from '../api/submissions';
import { getValidDates } from '../api/schedule';
import type { Submission, SubmissionStatus } from '../types/submission';
import CalendarView from '../components/dashboard/CalendarView';
import DayDetail from '../components/dashboard/DayDetail';

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-100 text-blue-800',
  ai_edited: 'bg-purple-100 text-purple-800',
  in_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  scheduled: 'bg-ui-clearwater-100 text-ui-clearwater-800',
  published: 'bg-gray-100 text-gray-800',
  rejected: 'bg-red-100 text-red-800',
  pending_info: 'bg-orange-100 text-orange-800',
};

const STATUS_LABELS: Record<string, string> = {
  new: 'New',
  ai_edited: 'AI Edited',
  in_review: 'In Review',
  approved: 'Approved',
  scheduled: 'Scheduled',
  published: 'Published',
  rejected: 'Rejected',
  pending_info: 'Pending Info',
};

const CATEGORY_LABELS: Record<string, string> = {
  faculty_staff: 'Faculty/Staff',
  student: 'Student',
  job_opportunity: 'Job Opportunity',
  kudos: 'Kudos',
  in_memoriam: 'In Memoriam',
  news_release: 'News Release',
  calendar_event: 'Calendar Event',
};

const NEWSLETTER_LABELS: Record<string, string> = {
  tdr: 'TDR',
  myui: 'My UI',
  both: 'Both',
};

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [newsletterFilter, setNewsletterFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('list');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [validDates, setValidDates] = useState<Map<string, string[]>>(new Map());

  const fetchSubmissions = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof listSubmissions>[0] = {
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        target_newsletter: newsletterFilter || undefined,
        search: searchQuery || undefined,
        limit: 200,
      };

      if (viewMode === 'calendar') {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();
        params.date_from = toISODate(new Date(year, month, 1));
        params.date_to = toISODate(new Date(year, month + 1, 0));
      }

      const data = await listSubmissions(params);
      setSubmissions(data.Items);
      setTotal(data.Total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load submissions');
    } finally {
      setLoading(false);
    }
  };

  const fetchValidDates = async () => {
    try {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth();
      const from = toISODate(new Date(year, month, 1));
      const to = toISODate(new Date(year, month + 1, 0));
      const data = await getValidDates(from, to);
      const map = new Map<string, string[]>();
      for (const d of data.dates) {
        map.set(d.date, d.newsletters);
      }
      setValidDates(map);
    } catch {
      // Non-critical — calendar still works without valid dates
    }
  };

  useEffect(() => {
    fetchSubmissions();
    if (viewMode === 'calendar') fetchValidDates();
  }, [statusFilter, categoryFilter, newsletterFilter, viewMode, currentMonth]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchSubmissions();
  };

  const getStatusAction = (status: SubmissionStatus) => {
    switch (status) {
      case 'new':
        return 'Run AI Edit';
      case 'ai_edited':
        return 'Review Edit';
      case 'in_review':
        return 'Finalize';
      case 'approved':
        return 'Schedule';
      default:
        return 'View';
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Editor Dashboard</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {total} submission{total !== 1 ? 's' : ''}
          </span>
          <div className="flex rounded-md border border-gray-300 overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1.5 text-xs font-medium ${
                viewMode === 'list'
                  ? 'bg-ui-gold-500 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              List
            </button>
            <button
              onClick={() => setViewMode('calendar')}
              className={`px-3 py-1.5 text-xs font-medium border-l border-gray-300 ${
                viewMode === 'calendar'
                  ? 'bg-ui-gold-500 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              Calendar
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {Object.entries(STATUS_LABELS).map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Category</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Newsletter</label>
            <select
              value={newsletterFilter}
              onChange={(e) => setNewsletterFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="tdr">TDR</option>
              <option value="myui">My UI</option>
              <option value="both">Both</option>
            </select>
          </div>
          {viewMode === 'list' && (
            <form onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Search headlines, body, submitter..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-md hover:bg-gray-200"
              >
                Search
              </button>
            </form>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-4 text-red-400 hover:text-red-600">&times;</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : viewMode === 'calendar' ? (
        /* Calendar view */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <CalendarView
              submissions={submissions}
              selectedDate={selectedDate}
              onDateClick={setSelectedDate}
              currentMonth={currentMonth}
              onMonthChange={setCurrentMonth}
              validDates={validDates}
            />
          </div>
          <div>
            {selectedDate ? (
              <DayDetail date={selectedDate} submissions={submissions} />
            ) : (
              <div className="bg-white rounded-lg shadow p-8 text-center">
                <p className="text-sm text-gray-400">
                  Click a date to see scheduled submissions.
                </p>
              </div>
            )}
          </div>
        </div>
      ) : /* List view */
      submissions.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">No submissions found.</p>
          <p className="text-sm text-gray-400 mt-1">
            Submit an announcement using the Submit page.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {submissions.map((sub) => (
            <div
              key={sub.Id}
              className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => navigate(`/edit/${sub.Id}`)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[sub.Status] || 'bg-gray-100'}`}
                    >
                      {STATUS_LABELS[sub.Status] || sub.Status}
                    </span>
                    <span className="text-xs bg-gray-50 text-gray-600 px-2 py-0.5 rounded">
                      {CATEGORY_LABELS[sub.Category] || sub.Category}
                    </span>
                    <span className="text-xs bg-ui-gold-50 text-ui-gold-700 px-2 py-0.5 rounded font-medium">
                      {NEWSLETTER_LABELS[sub.Target_Newsletter]}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 truncate">
                    {sub.Original_Headline}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                    {sub.Original_Body}
                  </p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                    <span>{sub.Submitter_Name}</span>
                    <span>{new Date(sub.Created_At).toLocaleDateString()}</span>
                    {sub.Links.length > 0 && (
                      <span>{sub.Links.length} link{sub.Links.length > 1 ? 's' : ''}</span>
                    )}
                    {sub.Has_Image && <span>Has image</span>}
                    {sub.Schedule_Requests.length > 0 && (
                      <span>
                        {sub.Schedule_Requests[0].Requested_Date
                          ? `Run: ${new Date(sub.Schedule_Requests[0].Requested_Date + 'T12:00:00').toLocaleDateString()}`
                          : 'Schedule prefs'}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  className="ml-4 px-3 py-1.5 text-xs font-medium rounded-md bg-ui-gold-50 text-ui-gold-700 hover:bg-ui-gold-100 whitespace-nowrap"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/edit/${sub.Id}`);
                  }}
                >
                  {getStatusAction(sub.Status)}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
