export interface AIFlag {
  severity: 'error' | 'warning' | 'info';
  message: string;
  rule_key?: string;
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
