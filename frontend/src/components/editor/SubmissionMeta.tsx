import type { Submission } from '../../types/submission';

interface SubmissionMetaProps {
  submission: Submission;
}

const CATEGORY_LABELS: Record<string, string> = {
  faculty_staff: 'Faculty/Staff',
  student: 'Student',
  employee_announcement: 'Employee Announcement',
  job_opportunity: 'Job Opportunity',
  survey: 'Survey',
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
          {submission.Status === 'pending_info' && (
            <dd className="mt-1">
              <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">
                Info requested
              </span>
            </dd>
          )}
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
        {submission.Survey_End_Date && (
          <div>
            <dt className="text-xs text-gray-500">Survey Ends</dt>
            <dd className="text-gray-900">
              {new Date(submission.Survey_End_Date).toLocaleDateString(undefined, {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </dd>
          </div>
        )}
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
                {req.Is_Flexible && (
                  <span className="ml-1 inline-block px-1.5 py-0.5 text-xs font-normal bg-amber-100 text-amber-700 rounded">Flexible</span>
                )}
                {req.Repeat_Note && (
                  <span className="font-normal text-gray-500"> ({req.Repeat_Note})</span>
                )}
                {req.Is_Flexible && req.Flexible_Deadline && (
                  <dd className="text-xs text-gray-500 font-normal mt-0.5">Deadline: {req.Flexible_Deadline}</dd>
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
