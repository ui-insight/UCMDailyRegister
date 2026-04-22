export type SubmissionCategory =
  | 'faculty_staff'
  | 'student'
  | 'job_opportunity'
  | 'kudos'
  | 'in_memoriam'
  | 'employee_announcement'
  | 'survey'
  | 'news_release'
  | 'ucm_feature_story'
  | 'slc_event';

/** Legacy categories that may exist on old submissions but are no longer submittable. */
export type LegacyCategory = 'calendar_event';

/** "none" = SLC calendar only, no newsletter publication. */
export type TargetNewsletter = 'tdr' | 'myui' | 'both' | 'none';

export type EventClassification = 'strategic' | 'signature';

export type SubmissionStatus =
  | 'new'
  | 'ai_edited'
  | 'in_review'
  | 'approved'
  | 'scheduled'
  | 'published'
  | 'rejected'
  | 'pending_info';

export interface SubmissionLink {
  Id: string;
  Url: string;
  Anchor_Text: string | null;
  Display_Order: number;
}

export interface SubmissionScheduleRequest {
  Id: string;
  Requested_Date: string | null;
  Second_Requested_Date: string | null;
  Repeat_Count: number;
  Repeat_Note: string | null;
  Is_Flexible: boolean;
  Flexible_Deadline: string | null;
  Recurrence_Type: 'once' | 'weekly' | 'monthly_date' | 'monthly_nth_weekday';
  Recurrence_Interval: number;
  Recurrence_End_Date: string | null;
  Excluded_Dates: string[];
  Occurrence_Dates: string[];
}

export interface Submission {
  Id: string;
  Category: SubmissionCategory | LegacyCategory;
  Target_Newsletter: TargetNewsletter;
  Original_Headline: string;
  Original_Body: string;
  Submitter_Name: string;
  Submitter_Email: string;
  Submitter_Notes: string | null;
  Assigned_Editor: string | null;
  Editorial_Notes: string | null;
  Survey_End_Date: string | null;
  Has_Image: boolean;
  Image_Path: string | null;
  Status: SubmissionStatus;
  Show_In_SLC_Calendar: boolean;
  Event_Classification: EventClassification | null;
  Created_At: string;
  Updated_At: string;
  Links: SubmissionLink[];
  Schedule_Requests: SubmissionScheduleRequest[];
  Occurrence_Dates: string[];
}

export interface SubmissionCreate {
  Category: SubmissionCategory;
  Target_Newsletter: TargetNewsletter;
  Original_Headline: string;
  Original_Body: string;
  Submitter_Name: string;
  Submitter_Email: string;
  Submitter_Notes?: string;
  Survey_End_Date?: string;
  Show_In_SLC_Calendar?: boolean;
  Event_Classification?: EventClassification;
  Links?: { Url: string; Anchor_Text?: string }[];
  Schedule_Requests?: {
    Requested_Date?: string;
    Second_Requested_Date?: string;
    Repeat_Count?: number;
    Repeat_Note?: string;
    Is_Flexible?: boolean;
    Flexible_Deadline?: string;
    Recurrence_Type?: 'once' | 'weekly' | 'monthly_date' | 'monthly_nth_weekday';
    Recurrence_Interval?: number;
    Recurrence_End_Date?: string;
    Excluded_Dates?: string[];
  }[];
}
