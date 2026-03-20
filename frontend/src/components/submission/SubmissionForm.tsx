import { useEffect, useState } from 'react';
import { listAllowedValues } from '../../api/allowedValues';
import type { SubmissionCategory, TargetNewsletter, SubmissionCreate } from '../../types/submission';
import type { AllowedValue } from '../../types/allowedValue';
import { createSubmission } from '../../api/submissions';
import { getValidDates } from '../../api/schedule';
import { getSubmitterRole } from '../../utils/submitterRole';
import CategorySelect from './CategorySelect';
import NewsletterTargetSelect from './NewsletterTargetSelect';
import LinkEditor from './LinkEditor';
import SchedulePrefs from './SchedulePrefs';

/**
 * Public categories filtered by target newsletter. Staff-visibility
 * categories (e.g., news_release, ucm_feature_story) bypass this
 * filter — the backend already gates them via the X-User-Role header.
 */
const NEWSLETTER_CATEGORY_CODES: Record<TargetNewsletter, Set<string>> = {
  myui: new Set(['student', 'job_opportunity', 'survey']),
  tdr: new Set(['faculty_staff', 'job_opportunity', 'employee_announcement', 'kudos', 'in_memoriam', 'survey']),
  both: new Set(['faculty_staff', 'survey']),
};

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
  Recurrence_Type: 'once' | 'weekly' | 'monthly_date' | 'monthly_nth_weekday';
  Recurrence_Interval: number;
  Recurrence_End_Date: string;
}

const FALLBACK_CATEGORIES: AllowedValue[] = [
  {
    Id: 'faculty_staff',
    Value_Group: 'Submission_Category',
    Code: 'faculty_staff',
    Label: 'Faculty or Staff Announcement',
    Display_Order: 1,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: 'General faculty and staff announcements',
  },
  {
    Id: 'student',
    Value_Group: 'Submission_Category',
    Code: 'student',
    Label: 'Student Announcement',
    Display_Order: 2,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: 'Student-focused announcements',
  },
  {
    Id: 'employee_announcement',
    Value_Group: 'Submission_Category',
    Code: 'employee_announcement',
    Label: 'Employee Announcement',
    Display_Order: 3,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: 'Announcements for all employees',
  },
  {
    Id: 'job_opportunity',
    Value_Group: 'Submission_Category',
    Code: 'job_opportunity',
    Label: 'Job Opportunity',
    Display_Order: 4,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: 'Employment listings',
  },
  {
    Id: 'survey',
    Value_Group: 'Submission_Category',
    Code: 'survey',
    Label: 'Survey',
    Display_Order: 5,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: 'Research surveys and questionnaires',
  },
  {
    Id: 'kudos',
    Value_Group: 'Submission_Category',
    Code: 'kudos',
    Label: 'Acknowledgments and Kudos',
    Display_Order: 6,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: 'Awards, honors, recognition',
  },
  {
    Id: 'in_memoriam',
    Value_Group: 'Submission_Category',
    Code: 'in_memoriam',
    Label: 'In Memoriam',
    Display_Order: 7,
    Is_Active: true,
    Visibility_Role: 'public',
    Description: 'Memorial notices',
  },
];

export default function SubmissionForm() {
  const isStaff = getSubmitterRole() === 'staff';
  const [category, setCategory] = useState<SubmissionCategory>('faculty_staff');
  const [categories, setCategories] = useState<AllowedValue[]>(FALLBACK_CATEGORIES);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
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
    Recurrence_Type: 'once',
    Recurrence_Interval: 1,
    Recurrence_End_Date: '',
  });

  const [validDates, setValidDates] = useState<Set<string>>(new Set());

  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchCategories = async () => {
      setCategoriesLoading(true);
      try {
        const values = await listAllowedValues({ group: 'Submission_Category' });
        if (cancelled || values.length === 0) {
          return;
        }
        setCategories(values);
        setCategory((current) => (
          values.some((value) => value.Code === current)
            ? current
            : values[0].Code as SubmissionCategory
        ));
      } catch {
        if (!cancelled) {
          setCategories(FALLBACK_CATEGORIES);
        }
      } finally {
        if (!cancelled) {
          setCategoriesLoading(false);
        }
      }
    };

    fetchCategories();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch valid publication dates for the next 3 months
  useEffect(() => {
    const fetchDates = async () => {
      try {
        const today = new Date();
        const from = today.toISOString().split('T')[0];
        const future = new Date(today);
        future.setMonth(future.getMonth() + 3);
        const to = future.toISOString().split('T')[0];
        const nlType = targetNewsletter === 'both' ? undefined : targetNewsletter;
        const data = await getValidDates(from, to, nlType);
        setValidDates(new Set(data.dates.map((d) => d.date)));
      } catch {
        // Fallback to client-side validation if API unavailable
        setValidDates(new Set());
      }
    };
    fetchDates();
  }, [targetNewsletter]);

  // Filter categories by newsletter target; staff-visibility categories
  // (already gated by backend) always pass through
  const filteredCategories = categories.filter(
    (cat) =>
      cat.Visibility_Role === 'staff' ||
      NEWSLETTER_CATEGORY_CODES[targetNewsletter]?.has(cat.Code),
  );

  // Clear date and reset category when newsletter target changes
  const handleTargetChange = (target: TargetNewsletter) => {
    setTargetNewsletter(target);
    // validDates will be re-fetched via useEffect; clear date to be safe
    if (schedule.Requested_Date) {
      setSchedule({ ...schedule, Requested_Date: '' });
    }
    // Reset category if current selection isn't valid for the new newsletter
    // (staff categories are always valid so they won't trigger a reset)
    const allowed = NEWSLETTER_CATEGORY_CODES[target];
    const currentCat = categories.find((c) => c.Code === category);
    const isStaffCategory = currentCat?.Visibility_Role === 'staff';
    if (!isStaffCategory && !allowed?.has(category)) {
      const first = categories.find((c) => allowed?.has(c.Code));
      if (first) setCategory(first.Code as SubmissionCategory);
    }
  };

  const hasDateError = (): boolean => {
    if (!schedule.Requested_Date) return false;
    if (validDates.size > 0) {
      return !validDates.has(schedule.Requested_Date);
    }
    // Fallback client-side check
    const d = new Date(schedule.Requested_Date + 'T00:00:00');
    const day = d.getDay();
    if (targetNewsletter === 'myui' || targetNewsletter === 'both') return day !== 1;
    if (targetNewsletter === 'tdr') return day === 0 || day === 6;
    return false;
  };

  const hasRecurrenceEndError = (): boolean => (
    schedule.Recurrence_Type !== 'once'
    && !!schedule.Recurrence_End_Date
    && !!schedule.Requested_Date
    && schedule.Recurrence_End_Date < schedule.Requested_Date
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (hasDateError()) {
      setError('Please select a valid run date for the chosen newsletter.');
      return;
    }
    if (hasRecurrenceEndError()) {
      setError('Please choose a recurrence end date on or after the first run date.');
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
            Recurrence_Type: isStaff ? schedule.Recurrence_Type : 'once',
            Recurrence_Interval: isStaff ? schedule.Recurrence_Interval : 1,
            Recurrence_End_Date: isStaff ? schedule.Recurrence_End_Date || undefined : undefined,
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
      setSchedule({
        Requested_Date: '',
        Repeat_Count: 1,
        Repeat_Note: '',
        Is_Flexible: false,
        Flexible_Deadline: '',
        Recurrence_Type: 'once',
        Recurrence_Interval: 1,
        Recurrence_End_Date: '',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">
      {isStaff && (
        <div className="rounded-md bg-purple-50 border border-purple-200 px-4 py-2 flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-purple-500 px-2 py-0.5 text-xs font-medium text-white">
            Staff
          </span>
          <p className="text-sm text-purple-800">
            UCM staff mode — additional announcement types are available.
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
        <CategorySelect
          categories={filteredCategories}
          isLoading={categoriesLoading}
          value={category}
          onChange={setCategory}
        />
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
        <SchedulePrefs
          schedule={schedule}
          onChange={setSchedule}
          targetNewsletter={targetNewsletter}
          validDates={validDates.size > 0 ? validDates : undefined}
          showRecurrenceControls={isStaff}
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Additional Notes for Editors
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder=""
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

      {success && (
        <div className="rounded-md bg-green-50 border border-green-200 p-4">
          <p className="text-sm text-green-800">
            Submission received! An editor will review it for the newsletter.
          </p>
        </div>
      )}
    </form>
  );
}
