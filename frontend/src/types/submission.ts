export type SubmissionCategory =
  | 'faculty_staff'
  | 'student'
  | 'job_opportunity'
  | 'kudos'
  | 'in_memoriam';

/** Legacy categories that may exist on old submissions but are no longer submittable. */
export type LegacyCategory = 'news_release' | 'calendar_event';

export type TargetNewsletter = 'tdr' | 'myui' | 'both';

export type SubmissionStatus =
  | 'new'
  | 'ai_edited'
  | 'in_review'
  | 'approved'
  | 'scheduled'
  | 'published'
  | 'rejected';

export interface SubmissionLink {
  Id: string;
  Url: string;
  Anchor_Text: string | null;
  Display_Order: number;
}

export interface SubmissionScheduleRequest {
  Id: string;
  Requested_Date: string | null;
  Repeat_Count: number;
  Repeat_Note: string | null;
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
  Has_Image: boolean;
  Image_Path: string | null;
  Status: SubmissionStatus;
  Created_At: string;
  Updated_At: string;
  Links: SubmissionLink[];
  Schedule_Requests: SubmissionScheduleRequest[];
}

export interface SubmissionCreate {
  Category: SubmissionCategory;
  Target_Newsletter: TargetNewsletter;
  Original_Headline: string;
  Original_Body: string;
  Submitter_Name: string;
  Submitter_Email: string;
  Submitter_Notes?: string;
  Links?: { Url: string; Anchor_Text?: string }[];
  Schedule_Requests?: { Requested_Date?: string; Repeat_Count?: number; Repeat_Note?: string }[];
}
