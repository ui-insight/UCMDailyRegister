export interface AIFlag {
  type: 'error' | 'warning' | 'info';
  rule_key: string;
  message: string;
}

export interface AIEditLink {
  url: string;
  anchor_text: string;
}

export interface DiffSegment {
  type: 'equal' | 'insert' | 'delete' | 'replace';
  original: string;
  modified: string;
}

export interface TextDiff {
  segments: DiffSegment[];
  change_count: number;
  similarity_ratio: number;
}

export interface AIEditResponse {
  Submission_Id: string;
  Newsletter_Type: 'tdr' | 'myui';
  Edited_Headline: string;
  Edited_Body: string;
  Headline_Case: 'sentence_case' | 'title_case';
  Changes_Made: string[];
  Flags: AIFlag[];
  Embedded_Links: AIEditLink[];
  Confidence: number;
  AI_Provider: string;
  AI_Model: string;
  Headline_Diff: TextDiff;
  Body_Diff: TextDiff;
  Edit_Version_Id: string;
}

export interface EditVersion {
  Id: string;
  Submission_Id: string;
  Version_Type: 'original' | 'ai_suggested' | 'editor_final';
  Headline: string;
  Body: string;
  Headline_Case: 'sentence_case' | 'title_case' | null;
  Flags: AIFlag[] | null;
  Changes_Made: string[] | null;
  AI_Provider: string | null;
  AI_Model: string | null;
  Created_At: string;
}

export interface StyleRule {
  Id: string;
  Rule_Set: 'shared' | 'tdr' | 'myui';
  Category: string;
  Rule_Key: string;
  Rule_Text: string;
  Is_Active: boolean;
  Severity: 'error' | 'warning' | 'info';
}
