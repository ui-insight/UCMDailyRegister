import type { Submission } from '../../types/submission';

interface SubmissionMetaProps {
  submission: Submission;
}

const CATEGORY_LABELS: Record<string, string> = {
  faculty_staff: 'Faculty/Staff',
  student: 'Student',
  job_opportunity: 'Job Opportunity',
  kudos: 'Kudos',
  in_memoriam: 'In Memoriam',
  news_release: 'News Release',
  calendar_event: 'Calendar Event',
};

export default function SubmissionMeta({ submission }: SubmissionMetaProps) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Submission Info</h3>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-xs text-gray-500">Submitter</dt>
          <dd className="text-gray-900">{submission.submitter_name}</dd>
          <dd className="text-xs text-gray-500">{submission.submitter_email}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Category</dt>
          <dd className="text-gray-900">
            {CATEGORY_LABELS[submission.category] || submission.category}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Submitted</dt>
          <dd className="text-gray-900">
            {new Date(submission.created_at).toLocaleString()}
          </dd>
        </div>
        {submission.links.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500">Links</dt>
            {submission.links.map((link) => (
              <dd key={link.id} className="text-xs">
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all"
                >
                  {link.anchor_text || link.url}
                </a>
              </dd>
            ))}
          </div>
        )}
        {submission.submitter_notes && (
          <div>
            <dt className="text-xs text-gray-500">Submitter Notes</dt>
            <dd className="text-gray-700 text-xs bg-gray-50 p-2 rounded mt-1">
              {submission.submitter_notes}
            </dd>
          </div>
        )}
        {submission.schedule_requests.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500">Schedule Requests</dt>
            {submission.schedule_requests.map((req) => (
              <dd key={req.id} className="text-xs text-gray-700">
                {req.requested_date
                  ? new Date(req.requested_date).toLocaleDateString()
                  : 'No specific date'}{' '}
                &middot; Run {req.repeat_count}x
                {req.repeat_note && ` (${req.repeat_note})`}
              </dd>
            ))}
          </div>
        )}
      </dl>
    </div>
  );
}
