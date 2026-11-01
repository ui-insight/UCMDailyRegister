import { ApiError } from '../../api/client';
import { addFieldError, type FieldErrors } from '../../utils/formValidation';
import { addDaysToISODate } from '../../utils/date';
import type { SubmissionCategory, SubmissionCreate, TargetNewsletter } from '../../types/submission';

export interface LinkEntry {
  Url: string;
  Anchor_Text: string;
}

export interface ScheduleEntry {
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

interface NewsletterTargetInput {
  isJobOpportunity: boolean;
  isPublicFacultyStaffFlow: boolean;
  alsoPublishInStudentNewsletter: boolean;
  targetNewsletter: TargetNewsletter;
}

export function resolveNewsletterTargets({
  isJobOpportunity,
  isPublicFacultyStaffFlow,
  alsoPublishInStudentNewsletter,
  targetNewsletter,
}: NewsletterTargetInput) {
  const combinesStudentDates = isPublicFacultyStaffFlow && alsoPublishInStudentNewsletter;
  let effectiveTargetNewsletter = targetNewsletter;
  if (isJobOpportunity) {
    effectiveTargetNewsletter = 'tdr';
  } else if (isPublicFacultyStaffFlow) {
    effectiveTargetNewsletter = alsoPublishInStudentNewsletter ? 'both' : 'tdr';
  }
  return {
    combinesStudentDates,
    effectiveTargetNewsletter,
    scheduleTargetNewsletter: (combinesStudentDates ? 'tdr' : effectiveTargetNewsletter) as TargetNewsletter,
  };
}

export interface SubmissionFormValues {
  category: SubmissionCategory;
  targetNewsletter: TargetNewsletter;
  headline: string;
  body: string;
  submitterName: string;
  submitterEmail: string;
  notes: string;
  surveyEndDate: string;
  links: LinkEntry[];
  schedule: ScheduleEntry;
  preferredStudentDates: string[];
  isStaff: boolean;
  combinesStudentDates: boolean;
  isJobOpportunity: boolean;
  jobUrl: string;
  jobTitle: string;
  jobDepartment: string;
  jobLocation: string;
  jobRemoveDate: string;
}

function buildContent(values: SubmissionFormValues) {
  const { isJobOpportunity, jobTitle, jobDepartment, jobLocation, jobUrl } = values;
  if (!isJobOpportunity) {
    return {
      headline: values.headline,
      body: values.body,
      links: values.links
        .filter((l) => l.Url.trim())
        .map((l) => ({ Url: l.Url, Anchor_Text: l.Anchor_Text || undefined })),
    };
  }

  // For jobs, compose headline/body/links from structured fields
  const jobAnchorText = [jobTitle, jobDepartment, jobLocation].filter(Boolean).join(', ');
  const jobBodyParts = [
    jobDepartment ? `Department: ${jobDepartment}.` : null,
    jobLocation ? `Location: ${jobLocation}.` : null,
    'Apply using the linked posting.',
  ].filter(Boolean);
  return {
    headline: jobTitle,
    body: jobBodyParts.join(' '),
    links: jobUrl.trim() ? [{ Url: jobUrl, Anchor_Text: jobAnchorText || undefined }] : [],
  };
}

function buildScheduleRequests(
  values: SubmissionFormValues,
): NonNullable<SubmissionCreate['Schedule_Requests']> {
  const { schedule, isStaff, preferredStudentDates } = values;
  const baseScheduleRequest = {
    Repeat_Note: schedule.Repeat_Note || undefined,
    Is_Flexible: schedule.Is_Flexible || undefined,
    Flexible_Deadline: schedule.Flexible_Deadline || undefined,
    Recurrence_Type: isStaff ? schedule.Recurrence_Type : 'once' as const,
    Recurrence_Interval: isStaff ? schedule.Recurrence_Interval : 1,
    Recurrence_End_Date: isStaff ? schedule.Recurrence_End_Date || undefined : undefined,
  };

  if (values.isJobOpportunity) {
    return [{
      ...baseScheduleRequest,
      Requested_Date: schedule.Requested_Date,
      Second_Requested_Date: undefined,
      Repeat_Count: 1,
      Recurrence_Type: 'date_range',
      Recurrence_Interval: 1,
      Recurrence_End_Date: values.jobRemoveDate || (
        schedule.Requested_Date
          ? addDaysToISODate(schedule.Requested_Date, 13)
          : undefined
      ),
    }];
  }

  if (values.combinesStudentDates) {
    const tdrDates = [
      schedule.Requested_Date,
      ...(schedule.Repeat_Count >= 2 && schedule.Second_Requested_Date
        ? [schedule.Second_Requested_Date]
        : []),
    ];
    const combinedScheduleCount = Math.max(tdrDates.length, preferredStudentDates.length);
    return Array.from({ length: combinedScheduleCount }, (_, index) => ({
      ...baseScheduleRequest,
      Requested_Date: tdrDates[index] ?? tdrDates[0],
      Second_Requested_Date: preferredStudentDates[index] || undefined,
      Repeat_Count: 1,
    }));
  }

  return [{
    ...baseScheduleRequest,
    Requested_Date: schedule.Requested_Date,
    Second_Requested_Date: schedule.Second_Requested_Date || undefined,
    Repeat_Count: schedule.Repeat_Count,
  }];
}

export function buildSubmissionPayload(values: SubmissionFormValues): SubmissionCreate {
  const content = buildContent(values);
  return {
    Category: values.category,
    Target_Newsletter: values.targetNewsletter,
    Original_Headline: content.headline,
    Original_Body: content.body,
    Submitter_Name: values.submitterName,
    Submitter_Email: values.submitterEmail,
    Submitter_Notes: values.notes || undefined,
    Survey_End_Date: values.category === 'survey' && values.surveyEndDate ? values.surveyEndDate : undefined,
    Links: content.links,
    Schedule_Requests: buildScheduleRequests(values),
  };
}

interface ServerErrorContext {
  isJobOpportunity: boolean;
  combinesStudentDates: boolean;
  links: LinkEntry[];
  primaryDateId: string;
  secondDateId: string;
}

function fieldIdForLocation(location: unknown[], context: ServerErrorContext): string | undefined {
  if (location[0] === 'Links' && typeof location[1] === 'number') {
    if (context.isJobOpportunity) return 'submission-job-url';
    const slot = context.links.map((link, index) => ({ link, index }))
      .filter(({ link }) => link.Url.trim())[location[1]];
    const part = location.at(-1) === 'Anchor_Text' ? 'anchor' : 'url';
    return slot ? `submission-link-${slot.index}-${part}` : undefined;
  }
  if (location[0] === 'Schedule_Requests') {
    const scheduleFields: Record<string, string> = {
      Requested_Date: context.primaryDateId,
      Second_Requested_Date: context.combinesStudentDates
        ? `submission-student-date-${location[1]}`
        : context.secondDateId,
      Recurrence_End_Date: 'submission-recurrence-end-date',
      Recurrence_Interval: 'submission-recurrence-interval',
    };
    return scheduleFields[String(location.at(-1))];
  }
  const fields: Record<string, string> = {
    Original_Headline: context.isJobOpportunity ? 'submission-job-title' : 'submission-headline',
    Original_Body: 'submission-body',
    Submitter_Name: 'submission-submitter-name',
    Submitter_Email: 'submission-submitter-email',
    Survey_End_Date: 'submission-survey-end-date',
  };
  return fields[String(location[0])];
}

/** Map a 422 response onto form fields; returns nothing for any other error. */
export function mapServerFieldErrors(
  err: unknown,
  form: HTMLFormElement,
  context: ServerErrorContext,
): FieldErrors {
  const problems: FieldErrors = {};
  if (!(err instanceof ApiError) || err.status !== 422 || !Array.isArray(err.detail)) {
    return problems;
  }
  for (const problem of err.detail) {
    if (!problem || !Array.isArray(problem.loc) || typeof problem.msg !== 'string') continue;
    const location = problem.loc.filter((part: unknown) => part !== 'body');
    const id = fieldIdForLocation(location, context);
    if (id) addFieldError(problems, form, id, problem.msg);
  }
  return problems;
}
