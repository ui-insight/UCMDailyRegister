import { useCallback, useEffect, useState } from 'react';
import {
  getFeedbackGitHubExport,
  listFeedback,
  updateFeedback,
} from '../api/feedback';
import type { FeedbackStatus, FeedbackType, ProductFeedback } from '../types/feedback';
import { buildGitHubIssueUrl } from '../utils/feedback';
import { getSubmitterRole } from '../utils/submitterRole';
import { Button, Card, EmptyState, Toast, useToast } from '../components/common';

const STATUS_OPTIONS: Array<{ value: FeedbackStatus | ''; label: string }> = [
  { value: '', label: 'All' },
  { value: 'new', label: 'New' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'exported', label: 'Exported' },
  { value: 'closed', label: 'Closed' },
];

const TYPE_OPTIONS: Array<{ value: FeedbackType | ''; label: string }> = [
  { value: '', label: 'All' },
  { value: 'bug', label: 'Bugs' },
  { value: 'idea', label: 'Ideas' },
];

const STATUS_CLASSES: Record<FeedbackStatus, string> = {
  new: 'bg-status-attention-100 text-status-attention-800',
  reviewed: 'bg-status-info-100 text-status-info-800',
  exported: 'bg-status-success-100 text-status-success-800',
  closed: 'bg-status-muted-100 text-status-muted-800',
};

function formatDate(value: string) {
  return new Date(value).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default function FeedbackPage() {
  const isStaff = getSubmitterRole() === 'staff';
  const [items, setItems] = useState<ProductFeedback[]>([]);
  const [selected, setSelected] = useState<ProductFeedback | null>(null);
  const [statusFilter, setStatusFilter] = useState<FeedbackStatus | ''>('new');
  const [typeFilter, setTypeFilter] = useState<FeedbackType | ''>('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { toast, showToast, dismissToast } = useToast();

  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const feedback = await listFeedback({
        status: statusFilter,
        feedback_type: typeFilter,
      });
      setItems(feedback);
      setSelected((current) => {
        if (!current) return feedback[0] ?? null;
        return feedback.find((item) => item.Id === current.Id) ?? feedback[0] ?? null;
      });
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load feedback');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, typeFilter]);

  useEffect(() => {
    if (!isStaff) return;
    void loadData();
  }, [isStaff, loadData]);

  const handleStatusChange = async (item: ProductFeedback, status: FeedbackStatus) => {
    try {
      const updated = await updateFeedback(item.Id, { Status: status });
      setSelected(updated);
      showToast('Feedback updated');
      await loadData();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to update feedback', 'error');
    }
  };

  const handleCopyExport = async (item: ProductFeedback) => {
    try {
      const exported = await getFeedbackGitHubExport(item.Id);
      const url = buildGitHubIssueUrl(exported.Title, exported.Body);
      await navigator.clipboard.writeText(`${exported.Title}\n\n${exported.Body}`);
      showToast('GitHub-ready issue text copied');
      window.open(url, '_blank', 'noreferrer');
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to prepare GitHub export', 'error');
    }
  };

  const handleSaveGitHubUrl = async (item: ProductFeedback, url: string) => {
    try {
      const updated = await updateFeedback(item.Id, {
        GitHub_URL: url,
        Status: url ? 'exported' : item.Status,
      });
      setSelected(updated);
      showToast(url ? 'GitHub URL saved' : 'GitHub URL cleared');
      await loadData();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to save GitHub URL', 'error');
    }
  };

  if (!isStaff) {
    return (
      <Card className="p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">Feedback</h2>
        <p className="text-sm text-gray-600">The feedback queue is available to staff editors only.</p>
      </Card>
    );
  }

  return (
    <div>
      <Toast toast={toast} onDismiss={dismissToast} />
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Feedback</h2>
          <p className="mt-1 text-sm text-gray-500">
            Review in-app bug reports and feature ideas before exporting them to GitHub.
          </p>
        </div>
        <span className="rounded-md bg-white px-3 py-1.5 text-sm text-gray-500 shadow-sm">
          {items.length} item{items.length === 1 ? '' : 's'}
        </span>
      </div>

      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Status</label>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as FeedbackStatus | '')}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">Type</label>
            <select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value as FeedbackType | '')}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {TYPE_OPTIONS.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {loadError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {loadError}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading...</div>
      ) : items.length === 0 ? (
        <EmptyState
          title="No feedback matches these filters"
          description="New bug reports and feature ideas will appear here after users submit them from the app."
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="space-y-3">
            {items.map((item) => (
              <button
                key={item.Id}
                type="button"
                onClick={() => setSelected(item)}
                className={`w-full rounded-lg border bg-white p-4 text-left shadow-sm transition hover:border-ui-gold-300 ${
                  selected?.Id === item.Id ? 'border-ui-gold-400 ring-1 ring-ui-gold-200' : 'border-gray-200'
                }`}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium uppercase text-gray-600">
                    {item.Feedback_Type}
                  </span>
                  <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${STATUS_CLASSES[item.Status]}`}>
                    {item.Status}
                  </span>
                  <span className="ml-auto text-xs text-gray-400">{formatDate(item.Created_At)}</span>
                </div>
                <h3 className="text-sm font-semibold text-gray-900">{item.Summary}</h3>
                <p className="mt-1 line-clamp-2 text-xs text-gray-500">{item.Details}</p>
              </button>
            ))}
          </div>

          {selected && (
            <Card>
              <div className="mb-4 flex items-start justify-between gap-4">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] font-medium uppercase text-gray-600">
                      {selected.Feedback_Type}
                    </span>
                    <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${STATUS_CLASSES[selected.Status]}`}>
                      {selected.Status}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">{selected.Summary}</h3>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleCopyExport(selected)}
                >
                  Export to GitHub
                </Button>
              </div>

              <div className="prose prose-sm max-w-none">
                <p className="whitespace-pre-wrap text-sm text-gray-700">{selected.Details}</p>
              </div>

              <dl className="mt-5 grid grid-cols-1 gap-3 border-t border-gray-100 pt-4 text-sm md:grid-cols-2">
                <div>
                  <dt className="text-xs text-gray-500">Route</dt>
                  <dd className="font-mono text-xs text-gray-800">{selected.Route}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Mode</dt>
                  <dd className="text-gray-800">{selected.Submitter_Role}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Environment</dt>
                  <dd className="text-gray-800">{selected.App_Environment}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Contact</dt>
                  <dd className="text-gray-800">{selected.Contact_Email ?? 'Not provided'}</dd>
                </div>
                <div className="md:col-span-2">
                  <dt className="text-xs text-gray-500">Browser</dt>
                  <dd className="break-words font-mono text-xs text-gray-800">{selected.Browser}</dd>
                </div>
              </dl>

              <div className="mt-5 border-t border-gray-100 pt-4">
                <label className="mb-1 block text-xs text-gray-500">Status</label>
                <select
                  value={selected.Status}
                  onChange={(event) => void handleStatusChange(selected, event.target.value as FeedbackStatus)}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  {STATUS_OPTIONS.filter((option) => option.value).map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mt-4">
                <label htmlFor="feedback-github-url" className="mb-1 block text-xs text-gray-500">
                  GitHub issue URL
                </label>
                <div className="flex gap-2">
                  <input
                    id="feedback-github-url"
                    defaultValue={selected.GitHub_URL ?? ''}
                    key={selected.Id}
                    placeholder="https://github.com/ui-insight/UCMDailyRegister/issues/..."
                    className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
                    onBlur={(event) => {
                      if (event.target.value !== (selected.GitHub_URL ?? '')) {
                        void handleSaveGitHubUrl(selected, event.target.value);
                      }
                    }}
                  />
                  {selected.GitHub_URL && (
                    <a
                      href={selected.GitHub_URL}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Open
                    </a>
                  )}
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
