export interface BlackoutDate {
  Id: string;
  Blackout_Date: string;
  Newsletter_Type: string | null;
  Description: string | null;
  Is_Active: boolean;
}

export interface ValidPublicationDate {
  date: string;
  newsletters: string[];
}

export interface ValidDatesResponse {
  dates: ValidPublicationDate[];
  blackout_dates: BlackoutDate[];
}

export interface ScheduleModeOverride {
  Id: string;
  Newsletter_Type: string;
  Override_Mode: string;
  Start_Date: string;
  End_Date: string;
  Description: string | null;
}

export interface CustomPublishDate {
  Id: string;
  Newsletter_Type: string;
  Publish_Date: string;
  Description: string | null;
}
