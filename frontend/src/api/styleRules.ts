import { apiFetch } from './client';
import type { StyleRule } from '../types/aiEdit';

export async function listStyleRules(params?: {
  rule_set?: string;
  category?: string;
  active_only?: boolean;
}): Promise<StyleRule[]> {
  const searchParams = new URLSearchParams();
  if (params) {
    if (params.rule_set) searchParams.set('rule_set', params.rule_set);
    if (params.category) searchParams.set('category', params.category);
    if (params.active_only) searchParams.set('active_only', 'true');
  }
  const query = searchParams.toString();
  return apiFetch<StyleRule[]>(`/style-rules${query ? `?${query}` : ''}`);
}

export async function createStyleRule(data: {
  Rule_Set: string;
  Category: string;
  Rule_Key: string;
  Rule_Text: string;
  Severity?: string;
}): Promise<StyleRule> {
  return apiFetch<StyleRule>('/style-rules', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateStyleRule(
  id: string,
  data: Partial<{ Rule_Text: string; Is_Active: boolean; Severity: string; Category: string }>,
): Promise<StyleRule> {
  return apiFetch<StyleRule>(`/style-rules/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteStyleRule(id: string): Promise<void> {
  await apiFetch(`/style-rules/${id}`, { method: 'DELETE' });
}
