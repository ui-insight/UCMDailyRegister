export interface NewsletterSection {
  Id: string;
  Newsletter_Type: 'tdr' | 'myui';
  Name: string;
  Slug: string;
  Display_Order: number;
  Description: string | null;
  Requires_Image: boolean;
  Image_Dimensions: string | null;
  Is_Active: boolean;
}

export interface Newsletter {
  Id: string;
  Newsletter_Type: 'tdr' | 'myui';
  Publish_Date: string;
  Status: 'draft' | 'in_progress' | 'ready_for_review' | 'submitted' | 'published';
  Created_At: string;
  Updated_At: string;
}

export interface NewsletterItem {
  Id: string;
  Newsletter_Id: string;
  Submission_Id: string;
  Section_Id: string;
  Position: number;
  Final_Headline: string;
  Final_Body: string;
  Run_Number: number;
}

export interface NewsletterExternalItem {
  Id: string;
  Newsletter_Id: string;
  Section_Id: string;
  Source_Type: string;
  Source_Id: string;
  Source_Url: string | null;
  Event_Start: string | null;
  Event_End: string | null;
  Location: string | null;
  Position: number;
  Final_Headline: string;
  Final_Body: string;
}
