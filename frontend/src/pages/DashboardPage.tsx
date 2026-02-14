import { useEffect, useState } from 'react';
import { listSubmissions } from '../api/submissions';
import type { Submission } from '../types/submission';

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-100 text-blue-800',
  ai_edited: 'bg-purple-100 text-purple-800',
  in_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  scheduled: 'bg-indigo-100 text-indigo-800',
  published: 'bg-gray-100 text-gray-800',
  rejected: 'bg-red-100 text-red-800',
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

export default function DashboardPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const data = await listSubmissions({
        status: statusFilter || undefined,
        search: searchQuery || undefined,
      });
      setSubmissions(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch submissions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmissions();
  }, [statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchSubmissions();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Editor Dashboard</h2>
        <span className="text-sm text-gray-500">{total} submissions</span>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All</option>
            <option value="new">New</option>
            <option value="ai_edited">AI Edited</option>
            <option value="in_review">In Review</option>
            <option value="approved">Approved</option>
            <option value="scheduled">Scheduled</option>
            <option value="published">Published</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2 flex-1">
          <input
            type="text"
            placeholder="Search headlines, body text, or submitter..."
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
      </div>

      {/* Submission list */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : submissions.length === 0 ? (
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
              key={sub.id}
              className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[sub.status] || 'bg-gray-100'}`}
                    >
                      {sub.status.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-gray-400">
                      {CATEGORY_LABELS[sub.category] || sub.category}
                    </span>
                    <span className="text-xs text-gray-400">
                      {NEWSLETTER_LABELS[sub.target_newsletter]}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900">
                    {sub.original_headline}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                    {sub.original_body}
                  </p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                    <span>{sub.submitter_name}</span>
                    <span>{new Date(sub.created_at).toLocaleDateString()}</span>
                    {sub.links.length > 0 && (
                      <span>{sub.links.length} link{sub.links.length > 1 ? 's' : ''}</span>
                    )}
                    {sub.has_image && <span>Has image</span>}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
