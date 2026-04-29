import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Submission, SubmissionStatus } from '../../types/submission';
import { getOccurrenceDates } from '../../utils/submissionOccurrences';
import { rescheduleScheduleOccurrence } from '../../api/submissions';

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-status-info-100 text-status-info-800',
  ai_edited: 'bg-status-edited-100 text-status-edited-800',
  in_review: 'bg-status-warning-100 text-status-warning-800',
  approved: 'bg-status-success-100 text-status-success-800',
  scheduled: 'bg-ui-clearwater-100 text-ui-clearwater-800',
  published: 'bg-status-muted-100 text-status-muted-800',
  rejected: 'bg-status-error-100 text-status-error-800',
  pending_info: 'bg-status-attention-100 text-status-attention-800',
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

interface DayDetailProps {
  date: string;
  submissions: Submission[];
  onReschedule?: () => void;
}

function getStatusAction(status: SubmissionStatus): string {
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
}

export default function DayDetail({ date, submissions, onReschedule }: DayDetailProps) {
  const navigate = useNavigate();
  const [movingId, setMovingId] = useState<string | null>(null);
  const [moveDate, setMoveDate] = useState('');
  const [moveError, setMoveError] = useState<string | null>(null);

  const dateLabel = new Date(date + 'T12:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  // Filter to submissions that have this date in their schedule
  const daySubs = submissions.filter((sub) =>
    getOccurrenceDates(sub).includes(date),
  );

  const handleMove = async (sub: Submission) => {
    if (!moveDate) return;
    setMoveError(null);

    // Find the schedule request that contains this date
    const schedReq = sub.Schedule_Requests.find((sr) =>
      sr.Occurrence_Dates?.includes(date) ||
      sr.Requested_Date === date ||
      sr.Second_Requested_Date === date
    );

    if (!schedReq) {
      setMoveError('Could not find schedule request for this date');
      return;
    }

    try {
      await rescheduleScheduleOccurrence(sub.Id, schedReq.Id, date, moveDate);
      setMovingId(null);
      setMoveDate('');
      onReschedule?.();
    } catch (err) {
      setMoveError(err instanceof Error ? err.message : 'Failed to reschedule');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">{dateLabel}</h3>
        <span className="text-xs text-gray-400">
          {daySubs.length} submission{daySubs.length !== 1 ? 's' : ''}
        </span>
      </div>

      {moveError && (
        <div className="mx-4 mt-2 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
          {moveError}
          <button onClick={() => setMoveError(null)} className="ml-2 text-red-400">&times;</button>
        </div>
      )}

      {daySubs.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-gray-400">
          No submissions scheduled for this date.
        </div>
      ) : (
        <div className="divide-y divide-gray-50">
          {daySubs.map((sub) => (
            <div
              key={sub.Id}
              className="px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
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
                  <h4 className="text-sm font-semibold text-gray-900 truncate">
                    {sub.Original_Headline}
                  </h4>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                    {sub.Original_Body}
                  </p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                    <span>{sub.Submitter_Name}</span>
                    {sub.Links.length > 0 && (
                      <span>
                        {sub.Links.length} link{sub.Links.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>

                  {/* Reschedule UI */}
                  {movingId === sub.Id ? (
                    <div
                      className="mt-2 flex items-center gap-2"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="date"
                        value={moveDate}
                        onChange={(e) => setMoveDate(e.target.value)}
                        className="rounded border-gray-300 text-xs px-2 py-1"
                      />
                      <button
                        onClick={() => handleMove(sub)}
                        disabled={!moveDate}
                        className="px-2 py-1 text-xs bg-ui-gold-600 text-white rounded hover:bg-ui-gold-700 disabled:opacity-50"
                      >
                        Move
                      </button>
                      <button
                        onClick={() => { setMovingId(null); setMoveDate(''); }}
                        className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      className="mt-2 text-xs text-ui-clearwater-600 hover:text-ui-clearwater-800"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMovingId(sub.Id);
                        setMoveDate('');
                        setMoveError(null);
                      }}
                    >
                      Move to another date
                    </button>
                  )}
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
