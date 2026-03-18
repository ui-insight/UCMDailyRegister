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
