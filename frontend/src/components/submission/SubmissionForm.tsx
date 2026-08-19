import { useEffect, useRef, useState } from 'react';
import { listAllowedValues } from '../../api/allowedValues';
import type { SubmissionCategory, TargetNewsletter, SubmissionCreate } from '../../types/submission';
import type { AllowedValue } from '../../types/allowedValue';
import { createSubmission } from '../../api/submissions';
import { getValidDates } from '../../api/schedule';
import { getSubmitterRole } from '../../utils/submitterRole';
import {
  addDaysISO,
  addDaysToISODate,
  addMonthsISO,
  parseISODate,
  todayISO,
} from '../../utils/date';
import CategorySelect from './CategorySelect';
import NewsletterTargetSelect from './NewsletterTargetSelect';
import LinkEditor from './LinkEditor';
import SchedulePrefs from './SchedulePrefs';

/**
 * Public categories filtered by target newsletter. Staff-visibility
 * categories (e.g., news_release, ucm_feature_story) bypass this
 * filter — the backend authorizes staff-only fields via the trusted auth boundary.
 */
const NEWSLETTER_CATEGORY_CODES: Record<TargetNewsletter, Set<string>> = {
  myui: new Set(['student', 'survey']),
  tdr: new Set(['faculty_staff', 'job_opportunity', 'employee_announcement', 'kudos', 'in_memoriam', 'survey', 'news_release', 'ucm_feature_story']),
  both: new Set(['faculty_staff', 'survey']),
  // SLC-only events route through the dedicated SLC submission form, not this one.
  none: new Set<string>(),
};

const STUDENT_NEWSLETTER_GUIDANCE = 'Student newsletter submissions generally run once, during the week the event or opportunity occurs. Submissions may run twice when advance notice is needed, such as for registration, RSVP deadlines, ticket sales, reservations, applications or other time-sensitive deadlines. Staff will review and determine final publication dates.';

const PUBLIC_TDR_ONLY_CATEGORY_CODES = new Set([
  'employee_announcement',
  'in_memoriam',
  'job_opportunity',
  'kudos',
]);

interface LinkEntry {
  Url: string;
  Anchor_Text: string;
}

interface ScheduleEntry {
  Requested_Date: string;
  Second_Requested_Date: string;
  Repeat_Count: number;
  Repeat_Note: string;
  Is_Flexible: boolean;
  Flexible_Deadline: string;
  Recurrence_Type: 'once' | 'weekly' | 'monthly_date' | 'monthly_nth_weekday' | 'date_range';
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
  const [alsoPublishInStudentNewsletter, setAlsoPublishInStudentNewsletter] = useState(false);
  const [preferredStudentDates, setPreferredStudentDates] = useState<string[]>(['']);
  const getMinDate = (): string => addDaysISO(1);

  // Job Opportunity fields
  const [jobUrl, setJobUrl] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [jobDepartment, setJobDepartment] = useState('');
  const [jobLocation, setJobLocation] = useState('');
  const [jobRemoveDate, setJobRemoveDate] = useState('');
  const [links, setLinks] = useState<LinkEntry[]>([]);
  const [schedule, setSchedule] = useState<ScheduleEntry>({
    Requested_Date: '',
    Second_Requested_Date: '',
    Repeat_Count: 1,
    Repeat_Note: '',
    Is_Flexible: false,
    Flexible_Deadline: '',
    Recurrence_Type: 'once',
    Recurrence_Interval: 1,
    Recurrence_End_Date: '',
  });

  const [validDates, setValidDates] = useState<Set<string>>(new Set());
  const [secondaryValidDates, setSecondaryValidDates] = useState<Set<string>>(new Set());

  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const successRef = useRef<HTMLDivElement>(null);
  const isJobOpportunity = category === 'job_opportunity';
  const isPublicFacultyStaffFlow = !isStaff && category === 'faculty_staff';
  const effectiveTargetNewsletter: TargetNewsletter = isJobOpportunity
    ? 'tdr'
    : isPublicFacultyStaffFlow
      ? alsoPublishInStudentNewsletter ? 'both' : 'tdr'
      : targetNewsletter;
  const scheduleTargetNewsletter: TargetNewsletter = isPublicFacultyStaffFlow
    && alsoPublishInStudentNewsletter
      ? 'tdr'
      : effectiveTargetNewsletter;

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

  useEffect(() => {
    if (!isJobOpportunity || targetNewsletter === 'tdr') {
      return;
    }

    setTargetNewsletter('tdr');
    setSchedule((current) => ({
      ...current,
      Requested_Date: '',
      Second_Requested_Date: '',
      Repeat_Count: 1,
    }));
  }, [isJobOpportunity, targetNewsletter]);

  // Fetch valid publication dates for the next 3 months
  useEffect(() => {
    const fetchDates = async () => {
      try {
        const from = todayISO();
        const to = addMonthsISO(3);
        if (effectiveTargetNewsletter === 'both') {
          const [tdrData, myUIData] = await Promise.all([
            getValidDates(from, to, 'tdr'),
            getValidDates(from, to, 'myui'),
          ]);
          setValidDates(new Set(
            tdrData.dates
              .filter((d) => d.newsletters.includes('tdr'))
              .map((d) => d.date),
          ));
          setSecondaryValidDates(new Set(
            myUIData.dates
              .filter((d) => d.newsletters.includes('myui'))
              .map((d) => d.date),
          ));
          return;
        }

        const data = await getValidDates(from, to, effectiveTargetNewsletter);
        setValidDates(new Set(data.dates.map((d) => d.date)));
        setSecondaryValidDates(new Set());
      } catch {
        // Fallback to client-side validation if API unavailable
        setValidDates(new Set());
        setSecondaryValidDates(new Set());
      }
    };
    fetchDates();
  }, [effectiveTargetNewsletter]);

  // Public submitters choose an announcement type first. Newsletter targeting
  // follows from that choice, except surveys, which retain the audience picker.
  // Staff retain the existing target-first workflow and category filtering.
  const filteredCategories = categories
    .filter(
      (cat) =>
        isStaff
          ? cat.Visibility_Role === 'staff'
            || NEWSLETTER_CATEGORY_CODES[effectiveTargetNewsletter]?.has(cat.Code)
          : cat.Visibility_Role === 'public',
    )
    .map((cat) =>
      cat.Code === 'faculty_staff'
        ? {
            ...cat,
            Label: isStaff
              ? effectiveTargetNewsletter === 'both' ? 'News and Updates' : cat.Label
              : 'Faculty/Staff and Student',
          }
        : cat
    );

  const resetDatesForTarget = (nextTarget: TargetNewsletter) => {
    setSchedule((current) => ({
      ...current,
      Requested_Date: '',
      Second_Requested_Date: '',
      Repeat_Count: nextTarget === 'both' ? 2 : 1,
    }));
  };

  // Clear date and reset category when newsletter target changes
  const handleTargetChange = (target: TargetNewsletter) => {
    const nextTarget = isJobOpportunity ? 'tdr' : target;
    setTargetNewsletter(nextTarget);
    // validDates will be re-fetched via useEffect; clear dates and adjust repeat count
    resetDatesForTarget(nextTarget);
    // Reset category if current selection isn't valid for the new newsletter
    // (staff categories are always valid so they won't trigger a reset)
    const allowed = NEWSLETTER_CATEGORY_CODES[nextTarget];
    const currentCat = categories.find((c) => c.Code === category);
    const isStaffCategory = currentCat?.Visibility_Role === 'staff';
    if (!isStaffCategory && !allowed?.has(category)) {
      const first = categories.find((c) => allowed?.has(c.Code));
      if (first) setCategory(first.Code as SubmissionCategory);
    }
  };

  const handleCategoryChange = (nextCategory: SubmissionCategory) => {
    setCategory(nextCategory);
    if (isStaff) {
      return;
    }

    setAlsoPublishInStudentNewsletter(false);
    setPreferredStudentDates(['']);

    let nextTarget = targetNewsletter;
    if (nextCategory === 'faculty_staff' || PUBLIC_TDR_ONLY_CATEGORY_CODES.has(nextCategory)) {
      nextTarget = 'tdr';
    } else if (nextCategory === 'student') {
      nextTarget = 'myui';
    }

    if (nextTarget !== targetNewsletter) {
      setTargetNewsletter(nextTarget);
      resetDatesForTarget(nextTarget);
    }
  };

  const handleStudentNewsletterChange = (checked: boolean) => {
    setAlsoPublishInStudentNewsletter(checked);
    setPreferredStudentDates(['']);
    setTargetNewsletter(checked ? 'both' : 'tdr');
  };

  const hasDateError = (): boolean => {
    if (!schedule.Requested_Date) return false;
    if (validDates.size > 0) {
      return !validDates.has(schedule.Requested_Date);
    }
    // Fallback client-side check
    const d = parseISODate(schedule.Requested_Date);
    const day = d.getDay();
    if (scheduleTargetNewsletter === 'myui') return day !== 1;
    if (scheduleTargetNewsletter === 'tdr' || scheduleTargetNewsletter === 'both') return day === 0 || day === 6;
    return false;
  };

  const getSecondDateError = (): string | null => {
    if (scheduleTargetNewsletter === 'both') {
      if (!schedule.Second_Requested_Date) {
        return 'Please select a valid My UI run date.';
      }
      if (secondaryValidDates.size > 0 && !secondaryValidDates.has(schedule.Second_Requested_Date)) {
        return 'Please select a valid My UI run date.';
      }
      const d = parseISODate(schedule.Second_Requested_Date);
      if (d.getDay() !== 1) {
        return 'Please select a valid My UI run date.';
      }
      return null;
    }

    if (schedule.Repeat_Count < 2 || !schedule.Second_Requested_Date) {
      return null;
    }
    if (validDates.size > 0 && !validDates.has(schedule.Second_Requested_Date)) {
      return 'Please select a valid second run date for the chosen newsletter.';
    }

    const d = parseISODate(schedule.Second_Requested_Date);
    const day = d.getDay();
    if (scheduleTargetNewsletter === 'myui' && day !== 1) {
      return 'Please select a valid second run date for the chosen newsletter.';
    }
    if (scheduleTargetNewsletter === 'tdr' && (day === 0 || day === 6)) {
      return 'Please select a valid second run date for the chosen newsletter.';
    }
    return null;
  };

  const getStudentDateError = (studentDate: string): string | null => {
    if (!studentDate) {
      return 'Please select a preferred Student newsletter publication date.';
    }
    if (secondaryValidDates.size > 0 && !secondaryValidDates.has(studentDate)) {
      return 'Please select a valid Student newsletter publication date.';
    }
    if (parseISODate(studentDate).getDay() !== 1) {
      return 'Please select a valid Student newsletter publication date.';
    }
    return null;
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
    const secondDateError = getSecondDateError();
    if (secondDateError) {
      setError(secondDateError);
      return;
    }
    if (alsoPublishInStudentNewsletter) {
      const studentDateError = preferredStudentDates
        .map(getStudentDateError)
        .find((dateError) => dateError !== null);
      if (studentDateError) {
        setError(studentDateError);
        return;
      }
      if (new Set(preferredStudentDates).size !== preferredStudentDates.length) {
        setError('Please choose different Student newsletter publication dates.');
        return;
      }
    }
    if (hasRecurrenceEndError()) {
      setError('Please choose a recurrence end date on or after the first run date.');
      return;
    }
    setSubmitting(true);
    setError(null);
    setSuccess(false);

    try {
      const isJob = isJobOpportunity;

      // For jobs, compose headline/body/links from structured fields
      const jobAnchorText = [jobTitle, jobDepartment, jobLocation].filter(Boolean).join(', ');
      const jobBodyParts = [
        jobDepartment ? `Department: ${jobDepartment}.` : null,
        jobLocation ? `Location: ${jobLocation}.` : null,
        'Apply using the linked posting.',
      ].filter(Boolean);
      const effectiveHeadline = isJob ? jobTitle : headline;
      const effectiveBody = isJob ? jobBodyParts.join(' ') : body;
      const effectiveLinks = isJob
        ? (jobUrl.trim() ? [{ Url: jobUrl, Anchor_Text: jobAnchorText || undefined }] : [])
        : links.filter((l) => l.Url.trim()).map((l) => ({ Url: l.Url, Anchor_Text: l.Anchor_Text || undefined }));

      const baseScheduleRequest = {
        Repeat_Note: schedule.Repeat_Note || undefined,
        Is_Flexible: schedule.Is_Flexible || undefined,
        Flexible_Deadline: schedule.Flexible_Deadline || undefined,
        Recurrence_Type: isStaff ? schedule.Recurrence_Type : 'once' as const,
        Recurrence_Interval: isStaff ? schedule.Recurrence_Interval : 1,
        Recurrence_End_Date: isStaff ? schedule.Recurrence_End_Date || undefined : undefined,
      };
      const tdrDates = [
        schedule.Requested_Date,
        ...(schedule.Repeat_Count >= 2 && schedule.Second_Requested_Date
          ? [schedule.Second_Requested_Date]
          : []),
      ];
      const combinedScheduleCount = Math.max(tdrDates.length, preferredStudentDates.length);
      const scheduleRequests: NonNullable<SubmissionCreate['Schedule_Requests']> =
        isJob
          ? [{
              ...baseScheduleRequest,
              Requested_Date: schedule.Requested_Date,
              Second_Requested_Date: undefined,
              Repeat_Count: 1,
              Recurrence_Type: 'date_range',
              Recurrence_Interval: 1,
              Recurrence_End_Date: jobRemoveDate || (
                schedule.Requested_Date
                  ? addDaysToISODate(schedule.Requested_Date, 13)
                  : undefined
              ),
            }]
          : isPublicFacultyStaffFlow && alsoPublishInStudentNewsletter
          ? Array.from({ length: combinedScheduleCount }, (_, index) => ({
              ...baseScheduleRequest,
              Requested_Date: tdrDates[index] ?? tdrDates[0],
              Second_Requested_Date: preferredStudentDates[index] || undefined,
              Repeat_Count: 1,
            }))
          : [
              {
                ...baseScheduleRequest,
                Requested_Date: schedule.Requested_Date,
                Second_Requested_Date: schedule.Second_Requested_Date || undefined,
                Repeat_Count: schedule.Repeat_Count,
              },
            ];

      const data: SubmissionCreate = {
        Category: category,
        Target_Newsletter: effectiveTargetNewsletter,
        Original_Headline: effectiveHeadline,
        Original_Body: effectiveBody,
        Submitter_Name: submitterName,
        Submitter_Email: submitterEmail,
        Submitter_Notes: notes || undefined,
        Survey_End_Date: category === 'survey' && surveyEndDate ? surveyEndDate : undefined,
        Links: effectiveLinks,
        Schedule_Requests: scheduleRequests,
      };

      await createSubmission(data);

      setSuccess(true);
      setTimeout(() => successRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
      // Reset form
      setHeadline('');
      setBody('');
      setNotes('');
      setSurveyEndDate('');
      setJobUrl('');
      setJobTitle('');
      setJobDepartment('');
      setJobLocation('');
      setJobRemoveDate('');
      setLinks([]);
      setAlsoPublishInStudentNewsletter(false);
      setPreferredStudentDates(['']);
      setTargetNewsletter('tdr');
      setCategory((filteredCategories[0]?.Code ?? 'faculty_staff') as SubmissionCategory);
      setSchedule({
        Requested_Date: '',
        Second_Requested_Date: '',
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
        <div className="rounded-md bg-ui-clearwater-50 border border-ui-clearwater-200 px-4 py-2 flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-ui-clearwater-500 px-2 py-0.5 text-xs font-medium text-white">
            Staff
          </span>
          <p className="text-sm text-ui-clearwater-800">
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
        {isJobOpportunity && (
          <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
            Job postings run in The Daily Register only.
          </p>
        )}
        {isStaff && (
          <NewsletterTargetSelect
            value={effectiveTargetNewsletter}
            onChange={handleTargetChange}
            disabledTargets={isJobOpportunity ? ['myui', 'both'] : undefined}
          />
        )}
        <CategorySelect
          categories={filteredCategories}
          isLoading={categoriesLoading}
          value={category}
          onChange={handleCategoryChange}
          helperText={isStaff
            ? 'Options vary by target newsletter.'
            : 'Select the announcement type that best matches your content.'}
        />
        {!isStaff && category === 'survey' && (
          <NewsletterTargetSelect
            value={effectiveTargetNewsletter}
            onChange={handleTargetChange}
            disabledTargets={isJobOpportunity ? ['myui', 'both'] : undefined}
          />
        )}
        {isPublicFacultyStaffFlow && (
          <div className="rounded-md border border-gray-200 bg-gray-50 px-4 py-3">
            <label
              htmlFor="submission-also-student-newsletter"
              className="flex items-start gap-3 text-sm font-medium text-gray-800"
            >
              <input
                id="submission-also-student-newsletter"
                type="checkbox"
                checked={alsoPublishInStudentNewsletter}
                onChange={(event) => handleStudentNewsletterChange(event.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-ui-gold-600 focus:ring-ui-gold-500"
              />
              <span>Also publish in Student newsletter</span>
            </label>
            {alsoPublishInStudentNewsletter && (
              <p className="mt-3 max-w-2xl text-sm leading-6 text-gray-600">
                {STUDENT_NEWSLETTER_GUIDANCE}
              </p>
            )}
          </div>
        )}
        {category === 'survey' && (
          <div>
            <label htmlFor="submission-survey-end-date" className="block text-sm font-medium text-gray-700 mb-1">
              Survey / Event End Date
            </label>
            <input
              id="submission-survey-end-date"
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
          {category === 'job_opportunity' ? 'Job Posting Details' : 'Content'}
        </h3>

        {category === 'job_opportunity' ? (
          /* --- Simplified Job Opportunity form --- */
          <div className="space-y-4">
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
              Job listings run in The Daily Register for two weeks. Provide the official U of I posting URL and position details below.
            </p>
            <div>
              <label htmlFor="submission-job-url" className="block text-sm font-medium text-gray-700 mb-1">
                Job Posting URL
              </label>
              <input
                id="submission-job-url"
                type="url"
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
                required
                placeholder="https://uidaho.peopleadmin.com/postings/..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Provide the specific official job posting link.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="submission-job-title" className="block text-sm font-medium text-gray-700 mb-1">
                  Position Title
                </label>
                <input
                  id="submission-job-title"
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  required
                  placeholder="e.g., Equal Opportunity specialist"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
              </div>
              <div>
                <label htmlFor="submission-job-department" className="block text-sm font-medium text-gray-700 mb-1">
                  Department
                </label>
                <input
                  id="submission-job-department"
                  type="text"
                  value={jobDepartment}
                  onChange={(e) => setJobDepartment(e.target.value)}
                  required
                  placeholder="e.g., Equal Opportunity and Compliance"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
              </div>
              <div>
                <label htmlFor="submission-job-location" className="block text-sm font-medium text-gray-700 mb-1">
                  Location(s)
                </label>
                <input
                  id="submission-job-location"
                  type="text"
                  value={jobLocation}
                  onChange={(e) => setJobLocation(e.target.value)}
                  placeholder="e.g., Moscow/off campus/hybrid possible"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Leave blank if Moscow only. Separate multiple locations with /.
                </p>
              </div>
            </div>
            <div>
              <label htmlFor="submission-job-remove-date" className="block text-sm font-medium text-gray-700 mb-1">
                Remove listing early? (optional)
              </label>
              <input
                id="submission-job-remove-date"
                type="date"
                value={jobRemoveDate}
                onChange={(e) => setJobRemoveDate(e.target.value)}
                min={schedule.Requested_Date || getMinDate()}
                max={schedule.Requested_Date
                  ? addDaysToISODate(schedule.Requested_Date, 13)
                  : undefined}
                className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                If the position closes before two weeks, select the date to stop running.
              </p>
            </div>
          </div>
        ) : (
          /* --- Standard announcement form --- */
          <>
            <div>
              <label htmlFor="submission-headline" className="block text-sm font-medium text-gray-700 mb-1">
                Headline
              </label>
              <input
                id="submission-headline"
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
              <label htmlFor="submission-body" className="block text-sm font-medium text-gray-700 mb-1">
                Body Text
              </label>
              <p className="text-xs text-gray-500 mb-2">
                Keep announcements concise — aim for 150–300 words. Include who, what, when, where, and cost if applicable.
              </p>
              <textarea
                id="submission-body"
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
          </>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-5">
        <h3 className="text-lg font-semibold text-gray-900 border-b pb-3">
          Scheduling
        </h3>
        <SchedulePrefs
          schedule={schedule}
          onChange={setSchedule}
          targetNewsletter={scheduleTargetNewsletter}
          validDates={validDates.size > 0 ? validDates : undefined}
          secondaryValidDates={secondaryValidDates.size > 0 ? secondaryValidDates : undefined}
          showRecurrenceControls={isStaff && !isJobOpportunity}
          showRepeatCount={!isJobOpportunity}
          heading={isPublicFacultyStaffFlow && alsoPublishInStudentNewsletter
            ? 'Daily Register publication preferences'
            : undefined}
          preferredDateLabel={isPublicFacultyStaffFlow && alsoPublishInStudentNewsletter
            ? 'Preferred Daily Register publication date'
            : undefined}
          secondDateLabel={isPublicFacultyStaffFlow && alsoPublishInStudentNewsletter
            ? 'Second Daily Register publication date'
            : undefined}
        />
        {isPublicFacultyStaffFlow && alsoPublishInStudentNewsletter && (
          <fieldset className="space-y-3 rounded-md border border-gray-200 px-4 py-4">
            <legend className="px-1 text-sm font-medium text-gray-700">
              Preferred Student newsletter publication dates
            </legend>
            {preferredStudentDates.map((studentDate, index) => {
              const studentDateError = studentDate ? getStudentDateError(studentDate) : null;
              return (
                <div key={index} className="flex flex-col gap-2 sm:flex-row sm:items-start">
                  <div className="w-full max-w-xs">
                    <label
                      htmlFor={`submission-student-date-${index}`}
                      className="block text-xs text-gray-500 mb-1"
                    >
                      {index === 0
                        ? 'Preferred Student newsletter publication date'
                        : `Additional preferred Student date ${index + 1}`}
                    </label>
                    <input
                      id={`submission-student-date-${index}`}
                      type="date"
                      value={studentDate}
                      onChange={(event) => setPreferredStudentDates((current) => (
                        current.map((dateValue, dateIndex) => (
                          dateIndex === index ? event.target.value : dateValue
                        ))
                      ))}
                      required
                      min={getMinDate()}
                      aria-invalid={studentDateError ? true : undefined}
                      className={`w-full rounded-md border px-3 py-2 text-sm focus:ring-1 ${
                        studentDateError
                          ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
                          : 'border-gray-300 focus:border-ui-gold-500 focus:ring-ui-gold-500'
                      }`}
                    />
                    {studentDateError && (
                      <p className="mt-1 text-xs text-red-600">{studentDateError}</p>
                    )}
                    <p className="mt-1 text-xs text-gray-400">
                      Select a valid Student newsletter publication date.
                    </p>
                  </div>
                  {preferredStudentDates.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setPreferredStudentDates((current) => (
                        current.filter((_, dateIndex) => dateIndex !== index)
                      ))}
                      className="mt-0 text-sm text-red-700 hover:text-red-800 sm:mt-6"
                      aria-label={`Remove preferred Student date ${index + 1}`}
                    >
                      Remove
                    </button>
                  )}
                </div>
              );
            })}
            <button
              type="button"
              onClick={() => setPreferredStudentDates((current) => [...current, ''])}
              className="text-sm font-medium text-ui-clearwater-700 hover:text-ui-clearwater-800"
            >
              + Add another Student newsletter date
            </button>
          </fieldset>
        )}
        <div>
          <label htmlFor="submission-editor-notes" className="block text-sm font-medium text-gray-700 mb-1">
            Additional Notes for Editors
          </label>
          <textarea
            id="submission-editor-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder=""
            autoComplete="off"
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
            <label htmlFor="submission-submitter-name" className="block text-sm font-medium text-gray-700 mb-1">
              Your Name
            </label>
            <input
              id="submission-submitter-name"
              type="text"
              value={submitterName}
              onChange={(e) => setSubmitterName(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
            />
          </div>
          <div>
            <label htmlFor="submission-submitter-email" className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <input
              id="submission-submitter-email"
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
          className="px-6 py-3 bg-ui-gold-500 text-ui-black font-medium rounded-lg hover:bg-ui-gold-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? 'Submitting...' : 'Submit Announcement'}
        </button>
      </div>

      {success && (
        <div ref={successRef} className="rounded-md bg-green-50 border border-green-200 p-4">
          <p className="text-sm text-green-800">
            Submission received! An editor will review it for the newsletter.
          </p>
        </div>
      )}
    </form>
  );
}
