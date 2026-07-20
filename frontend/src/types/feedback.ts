export type FeedbackType = 'bug' | 'idea';
export type FeedbackStatus = 'new' | 'reviewed' | 'exported' | 'closed';
export type FeedbackNotificationStatus = 'pending' | 'sent' | 'failed' | 'disabled';

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
  Notification_Status: FeedbackNotificationStatus;
  Notification_Attempts: number;
  Notification_Sent_At: string | null;
  Notification_Last_Error: string | null;
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

export interface ProductFeedbackSummary {
  New_Count: number;
  Failed_Notification_Count: number;
  Pending_Notification_Count: number;
}
