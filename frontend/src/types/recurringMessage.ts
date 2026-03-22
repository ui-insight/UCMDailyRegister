export type RecurrenceType =
  | 'once'
  | 'weekly'
  | 'monthly_date'
  | 'monthly_nth_weekday'
  | 'date_range';

export interface RecurringMessage {
  Id: string;
  Newsletter_Type: 'tdr' | 'myui';
  Section_Id: string;
  Headline: string;
  Body: string;
  Start_Date: string;
  Recurrence_Type: RecurrenceType;
  Recurrence_Interval: number;
  End_Date: string | null;
  Excluded_Dates: string[];
  Is_Active: boolean;
  Created_At: string;
  Updated_At: string;
}

export interface RecurringMessageIssueCandidate {
  Id: string;
  Newsletter_Type: 'tdr' | 'myui';
  Section_Id: string;
  Headline: string;
  Body: string;
  Start_Date: string;
  Recurrence_Type: RecurrenceType;
  Recurrence_Interval: number;
  End_Date: string | null;
  Excluded_Dates: string[];
  Is_Active: boolean;
  Selected: boolean;
  Skipped: boolean;
}
