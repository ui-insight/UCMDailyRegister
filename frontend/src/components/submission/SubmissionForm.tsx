import { useState } from 'react';
import type { SubmissionCategory, TargetNewsletter, SubmissionCreate } from '../../types/submission';
import { createSubmission } from '../../api/submissions';
import CategorySelect from './CategorySelect';
import NewsletterTargetSelect from './NewsletterTargetSelect';
import LinkEditor from './LinkEditor';
import SchedulePrefs from './SchedulePrefs';

interface LinkEntry {
  Url: string;
  Anchor_Text: string;
}

interface ScheduleEntry {
  Requested_Date: string;
  Repeat_Count: number;
  Repeat_Note: string;
  Is_Flexible: boolean;
  Flexible_Deadline: string;
}

export default function SubmissionForm() {
  const [category, setCategory] = useState<SubmissionCategory>('faculty_staff');
  const [targetNewsletter, setTargetNewsletter] = useState<TargetNewsletter>('tdr');
  const [headline, setHeadline] = useState('');
  const [body, setBody] = useState('');
  const [submitterName, setSubmitterName] = useState('');
  const [submitterEmail, setSubmitterEmail] = useState('');
  const [notes, setNotes] = useState('');
  const [surveyEndDate, setSurveyEndDate] = useState('');
  const [links, setLinks] = useState<LinkEntry[]>([]);
  const [schedule, setSchedule] = useState<ScheduleEntry>({
    Requested_Date: '',
    Repeat_Count: 1,
    Repeat_Note: '',
    Is_Flexible: false,
    Flexible_Deadline: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clear date when newsletter target changes (previously valid date may now be invalid)
  const handleTargetChange = (target: TargetNewsletter) => {
    setTargetNewsletter(target);
    if (schedule.Requested_Date) {
      const d = new Date(schedule.Requested_Date + 'T00:00:00');
      const day = d.getDay();
      const invalid =
        (target === 'myui' || target === 'both') ? day !== 1 :
        (target === 'tdr') ? (day === 0 || day === 6) : false;
      if (invalid) {
        setSchedule({ ...schedule, Requested_Date: '' });
      }
    }
  };

  const hasDateError = (): boolean => {
    if (!schedule.Requested_Date) return false;
    const d = new Date(schedule.Requested_Date + 'T00:00:00');
    const day = d.getDay();
    if (targetNewsletter === 'myui' || targetNewsletter === 'both') return day !== 1;
    if (targetNewsletter === 'tdr') return day === 0 || day === 6;
    return false;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (hasDateError()) {
      setError('Please select a valid run date for the chosen newsletter.');
      return;
    }
    setSubmitting(true);
    setError(null);
    setSuccess(false);

    try {
      const data: SubmissionCreate = {
        Category: category,
        Target_Newsletter: targetNewsletter,
        Original_Headline: headline,
        Original_Body: body,
        Submitter_Name: submitterName,
        Submitter_Email: submitterEmail,
        Submitter_Notes: notes || undefined,
        Survey_End_Date: category === 'survey' && surveyEndDate ? surveyEndDate : undefined,
        Links: links
          .filter((l) => l.Url.trim())
          .map((l) => ({ Url: l.Url, Anchor_Text: l.Anchor_Text || undefined })),
        Schedule_Requests: [
          {
            Requested_Date: schedule.Requested_Date,
            Repeat_Count: schedule.Repeat_Count,
            Repeat_Note: schedule.Repeat_Note || undefined,
            Is_Flexible: schedule.Is_Flexible || undefined,
            Flexible_Deadline: schedule.Flexible_Deadline || undefined,
          },
        ],
      };

      await createSubmission(data);

      setSuccess(true);
      // Reset form
      setHeadline('');
      setBody('');
      setNotes('');
      setSurveyEndDate('');
      setLinks([]);
      setSchedule({ Requested_Date: '', Repeat_Count: 1, Repeat_Note: '', Is_Flexible: false, Flexible_Deadline: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">
      {success && (
        <div className="rounded-md bg-green-50 border border-green-200 p-4">
          <p className="text-sm text-green-800">
            Submission received! An editor will review it for the next newsletter.
          </p>
        </div>
      )}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 space-y-5">
        <h3 className="text-lg font-semibold text-gray-900 border-b pb-3">
          About Your Announcement
        </h3>
        <NewsletterTargetSelect value={targetNewsletter} onChange={handleTargetChange} />
        <CategorySelect value={category} onChange={setCategory} />
        {category === 'survey' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Survey / Event End Date
            </label>
            <input
              type="date"
              value={surveyEndDate}
              onChange={(e) => setSurveyEndDate(e.target.value)}
              required
              className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              When does this survey or registration close?
            </p>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-5">
        <h3 className="text-lg font-semibold text-gray-900 border-b pb-3">
          Content
        </h3>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Headline
          </label>
          <input
            type="text"
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            required
            maxLength={500}
            placeholder="e.g., 'Register for spring Pilates classes'"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          />
          <p className="text-xs text-gray-400 mt-1">{headline.length}/500</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Body Text
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Keep announcements concise — aim for 150–300 words. Include who, what, when, where, and cost if applicable.
          </p>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
            rows={8}
            placeholder="Describe your announcement briefly. Include essential details: dates, times, location, cost, and how to participate or register."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          />
          <p className={`text-xs mt-1 ${
            (() => {
              const wc = body.trim() ? body.trim().split(/\s+/).length : 0;
              if (wc > 500) return 'text-red-500';
              if (wc > 300) return 'text-amber-500';
              return 'text-gray-400';
            })()
          }`}>
            {body.trim() ? body.trim().split(/\s+/).length : 0} words
          </p>
        </div>
        <LinkEditor links={links} onChange={setLinks} />
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-5">
        <h3 className="text-lg font-semibold text-gray-900 border-b pb-3">
          Scheduling
        </h3>
        <SchedulePrefs schedule={schedule} onChange={setSchedule} targetNewsletter={targetNewsletter} />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Additional Notes for Editors
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="e.g., 'Please run this on April 3. Link the text &quot;vandalsgive.uidaho.edu&quot; to https://vandalsgive.uidaho.edu/giving-day/98415'"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
          />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-5">
        <h3 className="text-lg font-semibold text-gray-900 border-b pb-3">
          Your Information
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your Name
            </label>
            <input
              type="text"
              value={submitterName}
              onChange={(e) => setSubmitterName(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={submitterEmail}
              onChange={(e) => setSubmitterEmail(e.target.value)}
              required
              placeholder="you@uidaho.edu"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={submitting}
          className="px-6 py-3 bg-ui-gold-600 text-white font-medium rounded-lg hover:bg-ui-gold-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? 'Submitting...' : 'Submit Announcement'}
        </button>
      </div>
    </form>
  );
}
