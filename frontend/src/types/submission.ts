export type SubmissionCategory =
  | 'faculty_staff'
  | 'student'
  | 'job_opportunity'
  | 'kudos'
  | 'in_memoriam'
  | 'news_release'
  | 'calendar_event';

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
  id: string;
  url: string;
  anchor_text: string | null;
  display_order: number;
}

export interface SubmissionScheduleRequest {
  id: string;
  requested_date: string | null;
  repeat_count: number;
  repeat_note: string | null;
}

export interface Submission {
  id: string;
  category: SubmissionCategory;
  target_newsletter: TargetNewsletter;
  original_headline: string;
  original_body: string;
  submitter_name: string;
  submitter_email: string;
  submitter_notes: string | null;
  has_image: boolean;
  image_path: string | null;
  status: SubmissionStatus;
  created_at: string;
  updated_at: string;
  links: SubmissionLink[];
  schedule_requests: SubmissionScheduleRequest[];
}

export interface SubmissionCreate {
  category: SubmissionCategory;
  target_newsletter: TargetNewsletter;
  original_headline: string;
  original_body: string;
  submitter_name: string;
  submitter_email: string;
  submitter_notes?: string;
  links?: { url: string; anchor_text?: string }[];
  schedule_requests?: { requested_date?: string; repeat_count?: number; repeat_note?: string }[];
}
