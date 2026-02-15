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
          <dd className="text-gray-900">{submission.Submitter_Name}</dd>
          <dd className="text-xs text-gray-500">{submission.Submitter_Email}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Category</dt>
          <dd className="text-gray-900">
            {CATEGORY_LABELS[submission.Category] || submission.Category}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Submitted</dt>
          <dd className="text-gray-900">
            {new Date(submission.Created_At).toLocaleString()}
          </dd>
        </div>
        {submission.Links.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500">Links</dt>
            {submission.Links.map((link) => (
              <dd key={link.Id} className="text-xs">
                <a
                  href={link.Url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all"
                >
                  {link.Anchor_Text || link.Url}
                </a>
              </dd>
            ))}
          </div>
        )}
        {submission.Submitter_Notes && (
          <div>
            <dt className="text-xs text-gray-500">Submitter Notes</dt>
            <dd className="text-gray-700 text-xs bg-gray-50 p-2 rounded mt-1">
              {submission.Submitter_Notes}
            </dd>
          </div>
        )}
        {submission.Schedule_Requests.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500">Schedule Requests</dt>
            {submission.Schedule_Requests.map((req) => (
              <dd key={req.Id} className="text-xs text-gray-700">
                {req.Requested_Date
                  ? new Date(req.Requested_Date).toLocaleDateString()
                  : 'No specific date'}{' '}
                &middot; Run {req.Repeat_Count}x
                {req.Repeat_Note && ` (${req.Repeat_Note})`}
              </dd>
            ))}
          </div>
        )}
      </dl>
    </div>
  );
}
