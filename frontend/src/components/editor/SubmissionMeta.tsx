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

const TARGET_LABELS: Record<string, string> = {
  tdr: 'The Daily Register',
  myui: 'My UI',
  both: 'Both Newsletters',
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
          <dt className="text-xs text-gray-500">Target Newsletter</dt>
          <dd className="text-gray-900">
            {TARGET_LABELS[submission.Target_Newsletter] || submission.Target_Newsletter}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Category</dt>
          <dd className="text-gray-900">
            {CATEGORY_LABELS[submission.Category] || submission.Category}
          </dd>
        </div>
        {submission.Schedule_Requests.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500">Requested Run Date</dt>
            {submission.Schedule_Requests.map((req) => (
              <dd key={req.Id} className="text-gray-900 font-medium">
                {req.Requested_Date
                  ? new Date(req.Requested_Date).toLocaleDateString(undefined, {
                      weekday: 'short',
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })
                  : 'No specific date'}
                {req.Repeat_Count > 1 && (
                  <span className="font-normal text-gray-500"> &middot; Run {req.Repeat_Count}x</span>
                )}
                {req.Repeat_Note && (
                  <span className="font-normal text-gray-500"> ({req.Repeat_Note})</span>
                )}
              </dd>
            ))}
          </div>
        )}
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
      </dl>
    </div>
  );
}
