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
  submission_id: string;
  newsletter_type: 'tdr' | 'myui';
  edited_headline: string;
  edited_body: string;
  headline_case: 'sentence_case' | 'title_case';
  changes_made: string[];
  flags: AIFlag[];
  embedded_links: AIEditLink[];
  confidence: number;
  ai_provider: string;
  ai_model: string;
  headline_diff: TextDiff;
  body_diff: TextDiff;
  edit_version_id: string;
}

export interface EditVersion {
  id: string;
  submission_id: string;
  version_type: 'original' | 'ai_suggested' | 'editor_final';
  headline: string;
  body: string;
  headline_case: 'sentence_case' | 'title_case' | null;
  flags: AIFlag[] | null;
  changes_made: string[] | null;
  ai_provider: string | null;
  ai_model: string | null;
  created_at: string;
}

export interface StyleRule {
  id: string;
  rule_set: 'shared' | 'tdr' | 'myui';
  category: string;
  rule_key: string;
  rule_text: string;
  is_active: boolean;
  severity: 'error' | 'warning' | 'info';
}
