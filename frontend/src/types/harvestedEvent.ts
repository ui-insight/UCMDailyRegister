// Mirrors backend/app/schemas/harvested_event.py exactly.

export type SLCReviewStatus = 'new' | 'flagged' | 'dismissed';

export interface HarvestedEvent {
  Id: string;
  Source_Type: string;
  Source_Id: string;
  Series_Id: string | null;
  Source_Url: string | null;
  Title: string;
  Description: string;
  Location: string | null;
  Event_Start: string;
  Event_End: string | null;
  All_Day: boolean;
  Category_Path: string | null;
  Is_Canceled: boolean;
  SLC_Review_Status: SLCReviewStatus;
  First_Seen_At: string;
  Last_Seen_At: string;
}

export interface HarvestedEventListResponse {
  Items: HarvestedEvent[];
  Total: number;
}

export interface HarvestSummary {
  Fetched: number;
  Created: number;
  Updated: number;
  Unchanged: number;
  Skipped: number;
}
