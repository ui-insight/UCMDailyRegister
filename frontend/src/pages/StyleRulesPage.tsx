import { useEffect, useState } from 'react';
import {
  listStyleRules,
  createStyleRule,
  updateStyleRule,
  deleteStyleRule,
} from '../api/styleRules';
import type { StyleRule } from '../types/aiEdit';

const SEVERITY_COLORS: Record<string, string> = {
  error: 'bg-red-100 text-red-800',
  warning: 'bg-ui-gold-100 text-ui-gold-800',
  info: 'bg-blue-100 text-blue-800',
};

const RULE_SET_LABELS: Record<string, string> = {
  shared: 'Shared',
  tdr: 'TDR',
  myui: 'My UI',
};

export default function StyleRulesPage() {
  const [rules, setRules] = useState<StyleRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [ruleSetFilter, setRuleSetFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [editSeverity, setEditSeverity] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  // New rule form
  const [newRuleSet, setNewRuleSet] = useState('shared');
  const [newCategory, setNewCategory] = useState('');
  const [newRuleKey, setNewRuleKey] = useState('');
  const [newRuleText, setNewRuleText] = useState('');
  const [newSeverity, setNewSeverity] = useState('warning');

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        const data = await listStyleRules({
          rule_set: ruleSetFilter || undefined,
          category: categoryFilter || undefined,
          active_only: !showInactive ? true : undefined,
        });
        setRules(data);
      } catch (err) {
        console.error('Failed to load rules:', err);
      } finally {
        setLoading(false);
      }
    })();
  }, [ruleSetFilter, categoryFilter, showInactive]);

  const loadRules = async () => {
    setLoading(true);
    try {
      const data = await listStyleRules({
        rule_set: ruleSetFilter || undefined,
        category: categoryFilter || undefined,
        active_only: !showInactive ? true : undefined,
      });
      setRules(data);
    } catch (err) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartEdit = (rule: StyleRule) => {
    setEditingId(rule.Id);
    setEditText(rule.Rule_Text);
    setEditSeverity(rule.Severity);
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;
    try {
      await updateStyleRule(editingId, {
        Rule_Text: editText,
        Severity: editSeverity,
      });
      setEditingId(null);
      showToast('Rule updated');
      loadRules();
    } catch (err) {
      console.error('Failed to update rule:', err);
    }
  };

  const handleToggleActive = async (rule: StyleRule) => {
    try {
      await updateStyleRule(rule.Id, { Is_Active: !rule.Is_Active });
      showToast(rule.Is_Active ? 'Rule deactivated' : 'Rule activated');
      loadRules();
    } catch (err) {
      console.error('Failed to toggle rule:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this rule permanently?')) return;
    try {
      await deleteStyleRule(id);
      showToast('Rule deleted');
      loadRules();
    } catch (err) {
      console.error('Failed to delete rule:', err);
    }
  };

  const handleAddRule = async () => {
    if (!newCategory || !newRuleKey || !newRuleText) return;
    try {
      await createStyleRule({
        Rule_Set: newRuleSet,
        Category: newCategory,
        Rule_Key: newRuleKey,
        Rule_Text: newRuleText,
        Severity: newSeverity,
      });
      setShowAddForm(false);
      setNewCategory('');
      setNewRuleKey('');
      setNewRuleText('');
      showToast('Rule created');
      loadRules();
    } catch (err) {
      console.error('Failed to create rule:', err);
    }
  };

  const showToast = (message: string) => {
    setToast(message);
    setTimeout(() => setToast(null), 3000);
  };

  // Get unique categories for filter
  const categories = [...new Set(rules.map((r) => r.Category))].sort();

  // Group rules by category
  const rulesByCategory = new Map<string, StyleRule[]>();
  for (const rule of rules) {
    const existing = rulesByCategory.get(rule.Category) || [];
    existing.push(rule);
    rulesByCategory.set(rule.Category, existing);
  }

  return (
    <div>
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Style Rules</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">{rules.length} rules</span>
          <button
            onClick={() => setShowAddForm(true)}
            className="px-3 py-1.5 text-sm font-medium rounded-md bg-ui-gold-600 text-white hover:bg-ui-gold-700"
          >
            + Add Rule
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Rule Set</label>
            <select
              value={ruleSetFilter}
              onChange={(e) => setRuleSetFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="shared">Shared</option>
              <option value="tdr">TDR</option>
              <option value="myui">My UI</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Category</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer pb-2">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded"
            />
            Show inactive
          </label>
        </div>
      </div>

      {/* Add Rule Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-4 mb-6 border-2 border-ui-gold-200">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Add New Rule</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Rule Set</label>
              <select
                value={newRuleSet}
                onChange={(e) => setNewRuleSet(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="shared">Shared</option>
                <option value="tdr">TDR</option>
                <option value="myui">My UI</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Category</label>
              <input
                type="text"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                placeholder="e.g., formatting, voice"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Rule Key</label>
              <input
                type="text"
                value={newRuleKey}
                onChange={(e) => setNewRuleKey(e.target.value)}
                placeholder="e.g., no_passive_voice"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="mb-3">
            <label className="block text-xs text-gray-500 mb-1">Rule Text</label>
            <textarea
              value={newRuleText}
              onChange={(e) => setNewRuleText(e.target.value)}
              rows={2}
              placeholder="Describe the editorial rule..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="flex items-center gap-3">
            <select
              value={newSeverity}
              onChange={(e) => setNewSeverity(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="error">Error (MUST)</option>
              <option value="warning">Warning (SHOULD)</option>
              <option value="info">Info (GUIDELINE)</option>
            </select>
            <button
              onClick={handleAddRule}
              className="px-4 py-2 text-sm font-medium rounded-md bg-ui-gold-600 text-white hover:bg-ui-gold-700"
            >
              Add Rule
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Rules list grouped by category */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : rules.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No rules found.
        </div>
      ) : (
        <div className="space-y-4">
          {[...rulesByCategory.entries()].map(([category, catRules]) => (
            <div key={category} className="bg-white rounded-lg shadow">
              <div className="px-4 py-3 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-900 capitalize">
                  {category.replace(/_/g, ' ')}
                </h3>
              </div>
              <div className="divide-y divide-gray-50">
                {catRules.map((rule) => (
                  <div
                    key={rule.Id}
                    className={`px-4 py-3 ${!rule.Is_Active ? 'opacity-50' : ''}`}
                  >
                    {editingId === rule.Id ? (
                      /* Editing mode */
                      <div className="space-y-2">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={2}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                        />
                        <div className="flex items-center gap-2">
                          <select
                            value={editSeverity}
                            onChange={(e) => setEditSeverity(e.target.value)}
                            className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                          >
                            <option value="error">Error</option>
                            <option value="warning">Warning</option>
                            <option value="info">Info</option>
                          </select>
                          <button
                            onClick={handleSaveEdit}
                            className="px-3 py-1 text-xs font-medium rounded bg-ui-gold-600 text-white hover:bg-ui-gold-700"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="px-3 py-1 text-xs text-gray-600 hover:text-gray-800"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Display mode */
                      <div className="flex items-start justify-between group">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`text-xs px-1.5 py-0.5 rounded font-medium ${SEVERITY_COLORS[rule.Severity]}`}
                            >
                              {rule.Severity}
                            </span>
                            <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                              {RULE_SET_LABELS[rule.Rule_Set]}
                            </span>
                            <span className="text-xs text-gray-400 font-mono">
                              {rule.Rule_Key}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700">{rule.Rule_Text}</p>
                        </div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                          <button
                            onClick={() => handleStartEdit(rule)}
                            className="p-1 text-gray-400 hover:text-ui-gold-600 text-xs"
                            title="Edit"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleToggleActive(rule)}
                            className="p-1 text-gray-400 hover:text-blue-600 text-xs"
                            title={rule.Is_Active ? 'Deactivate' : 'Activate'}
                          >
                            {rule.Is_Active ? 'Off' : 'On'}
                          </button>
                          <button
                            onClick={() => handleDelete(rule.Id)}
                            className="p-1 text-gray-400 hover:text-red-600 text-xs"
                            title="Delete"
                          >
                            Del
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
