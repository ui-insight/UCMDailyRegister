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
  Upstream_Changed_At: string | null;
  Promoted_Submission_Id: string | null;
  Promoted_Classification: 'strategic' | 'signature' | null;
  First_Seen_At: string;
  Last_Seen_At: string;
}

export interface HarvestedEventUpdate {
  SLC_Review_Status: SLCReviewStatus;
  Event_Classification?: 'strategic' | 'signature';
}

export interface HarvestedEventListResponse {
  Items: HarvestedEvent[];
  Total: number;
}

export type OpsReviewStatus = 'new' | 'reviewed' | 'dismissed';
export type OpsNeedConfidence = 'low' | 'medium' | 'high';

export interface OpsNeed {
  Need: string;
  Confidence: OpsNeedConfidence;
  Rationale: string;
}

// Mirrors OpsEventResponse: the ops lens deliberately excludes SLC fields.
export interface OpsEvent {
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
  Ops_Review_Status: OpsReviewStatus;
  Needs: OpsNeed[];
  Needs_Assessed: boolean;
  First_Seen_At: string;
  Last_Seen_At: string;
}

export interface OpsEventUpdate {
  Ops_Review_Status: OpsReviewStatus;
}

export interface OpsEventListResponse {
  Items: OpsEvent[];
  Total: number;
}

export interface HarvestSummary {
  Fetched: number;
  Created: number;
  Updated: number;
  Unchanged: number;
  Skipped: number;
  Canceled: number;
}
