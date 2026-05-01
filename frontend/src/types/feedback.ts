export type FeedbackType = 'bug' | 'idea';
export type FeedbackStatus = 'new' | 'reviewed' | 'exported' | 'closed';

export interface ProductFeedback {
  Id: string;
  Feedback_Type: FeedbackType;
  Summary: string;
  Details: string;
  Contact_Email: string | null;
  Submitter_Role: 'public' | 'staff' | 'slc';
  Route: string;
  App_Environment: string;
  Host: string;
  Browser: string;
  Viewport: string;
  Status: FeedbackStatus;
  GitHub_URL: string | null;
  Created_At: string;
  Updated_At: string;
}

export interface ProductFeedbackCreate {
  Feedback_Type: FeedbackType;
  Summary: string;
  Details: string;
  Contact_Email?: string | null;
  Submitter_Role: 'public' | 'staff' | 'slc';
  Route: string;
  App_Environment: string;
  Host: string;
  Browser: string;
  Viewport: string;
}

export interface ProductFeedbackExport {
  Title: string;
  Body: string;
}
