import { useCallback, useEffect, useState } from 'react';
import {
  createRecurringMessage,
  deleteRecurringMessage,
  listRecurringMessages,
  updateRecurringMessage,
} from '../api/recurringMessages';
import { listSections } from '../api/newsletters';
import type { NewsletterSection } from '../types/newsletter';
import type { RecurringMessage, RecurrenceType } from '../types/recurringMessage';
import { getSubmitterRole } from '../utils/submitterRole';

type NewsletterType = 'tdr' | 'myui';

interface RecurringMessageFormState {
  Newsletter_Type: NewsletterType;
  Section_Id: string;
  Headline: string;
  Body: string;
  Start_Date: string;
  Recurrence_Type: RecurrenceType;
  Recurrence_Interval: number;
  End_Date: string;
  Is_Active: boolean;
}

const EMPTY_FORM: RecurringMessageFormState = {
  Newsletter_Type: 'tdr',
  Section_Id: '',
  Headline: '',
  Body: '',
  Start_Date: '',
  Recurrence_Type: 'weekly',
  Recurrence_Interval: 1,
  End_Date: '',
  Is_Active: true,
};

function getCadenceLabel(form: Pick<
  RecurringMessageFormState,
  'Recurrence_Type' | 'Recurrence_Interval' | 'Start_Date' | 'End_Date'
>) {
  const interval = Math.max(form.Recurrence_Interval || 1, 1);
  switch (form.Recurrence_Type) {
    case 'once':
      return `One-time on ${form.Start_Date}`;
    case 'weekly':
      return interval === 1 ? `Weekly from ${form.Start_Date}` : `Every ${interval} weeks from ${form.Start_Date}`;
    case 'monthly_date':
      return interval === 1 ? 'Monthly on the same date' : `Every ${interval} months on the same date`;
    case 'monthly_nth_weekday':
      return interval === 1 ? 'Monthly on the same weekday pattern' : `Every ${interval} months on the same weekday pattern`;
    case 'date_range':
      return form.End_Date
        ? `Every issue from ${form.Start_Date} through ${form.End_Date}`
        : `Every issue starting ${form.Start_Date}`;
    default:
      return form.Start_Date;
  }
}

function toPayload(form: RecurringMessageFormState) {
  return {
    Newsletter_Type: form.Newsletter_Type,
    Section_Id: form.Section_Id,
    Headline: form.Headline.trim(),
    Body: form.Body.trim(),
    Start_Date: form.Start_Date,
    Recurrence_Type: form.Recurrence_Type,
    Recurrence_Interval: form.Recurrence_Interval,
    End_Date: form.End_Date || null,
    Is_Active: form.Is_Active,
  };
}

export default function RecurringMessagesPage() {
  const [messages, setMessages] = useState<RecurringMessage[]>([]);
  const [sections, setSections] = useState<NewsletterSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [newsletterFilter, setNewsletterFilter] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newForm, setNewForm] = useState<RecurringMessageFormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<RecurringMessageFormState>(EMPTY_FORM);
  const isStaff = getSubmitterRole() === 'staff';

  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [recurringMessages, tdrSections, myuiSections] = await Promise.all([
        listRecurringMessages({
          newsletter_type: newsletterFilter || undefined,
          active_only: !showInactive ? true : undefined,
        }),
        listSections('tdr'),
        listSections('myui'),
      ]);
      setMessages(recurringMessages);
      setSections([...tdrSections, ...myuiSections]);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load recurring messages');
    } finally {
      setLoading(false);
    }
  }, [newsletterFilter, showInactive]);

  useEffect(() => {
    if (!isStaff) return;
    void loadData();
  }, [isStaff, loadData]);

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 3000);
  };

  const getSectionsForType = (newsletterType: NewsletterType) => (
    sections.filter((section) => section.Newsletter_Type === newsletterType)
  );

  const startEdit = (message: RecurringMessage) => {
    setEditingId(message.Id);
    setEditForm({
      Newsletter_Type: message.Newsletter_Type,
      Section_Id: message.Section_Id,
      Headline: message.Headline,
      Body: message.Body,
      Start_Date: message.Start_Date,
      Recurrence_Type: message.Recurrence_Type,
      Recurrence_Interval: message.Recurrence_Interval,
      End_Date: message.End_Date ?? '',
      Is_Active: message.Is_Active,
    });
  };

  const handleCreate = async () => {
    if (!newForm.Section_Id || !newForm.Start_Date || !newForm.Headline.trim() || !newForm.Body.trim()) {
      return;
    }
    try {
      await createRecurringMessage(toPayload(newForm));
      setNewForm(EMPTY_FORM);
      setShowAddForm(false);
      showToast('Recurring message created');
      await loadData();
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to create recurring message');
    }
  };

  const handleSaveEdit = async () => {
    if (!editingId || !editForm.Section_Id || !editForm.Start_Date || !editForm.Headline.trim() || !editForm.Body.trim()) {
      return;
    }
    try {
      await updateRecurringMessage(editingId, toPayload(editForm));
      setEditingId(null);
      showToast('Recurring message updated');
      await loadData();
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to update recurring message');
    }
  };

  const handleToggleActive = async (message: RecurringMessage) => {
    try {
      await updateRecurringMessage(message.Id, { Is_Active: !message.Is_Active });
      showToast(message.Is_Active ? 'Recurring message deactivated' : 'Recurring message activated');
      await loadData();
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to update recurring message');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this recurring message?')) return;
    try {
      await deleteRecurringMessage(id);
      showToast('Recurring message deleted');
      await loadData();
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to delete recurring message');
    }
  };

  if (!isStaff) {
    return (
      <div className="bg-white rounded-lg shadow p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">Recurring Messages</h2>
        <p className="text-sm text-gray-600">
          This library is available to staff editors only. Open the app with
          <code className="bg-gray-100 px-1 py-0.5 rounded text-xs mx-1">?role=staff</code>
          to manage centrally scheduled editorial content.
        </p>
      </div>
    );
  }

  return (
    <div>
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Recurring Messages</h2>
          <p className="text-sm text-gray-500 mt-1">
            Manage centrally maintained editorial content that runs on a cadence.
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="px-3 py-1.5 text-sm font-medium rounded-md bg-ui-gold-600 text-white hover:bg-ui-gold-700"
        >
          + Add Recurring Message
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Newsletter</label>
            <select
              value={newsletterFilter}
              onChange={(event) => setNewsletterFilter(event.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="tdr">The Daily Register</option>
              <option value="myui">My UI</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer pb-2">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
              className="rounded"
            />
            Show inactive
          </label>
          <span className="text-sm text-gray-400">{messages.length} message{messages.length !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {loadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
          {loadError}
        </div>
      )}

      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-4 mb-6 border-2 border-ui-gold-200">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">New Recurring Message</h3>
          <RecurringMessageForm
            value={newForm}
            sections={getSectionsForType(newForm.Newsletter_Type)}
            onChange={setNewForm}
          />
          <div className="flex items-center gap-3 mt-4">
            <button
              onClick={() => void handleCreate()}
              className="px-4 py-2 text-sm font-medium rounded-md bg-ui-gold-600 text-white hover:bg-ui-gold-700"
            >
              Create Message
            </button>
            <button
              onClick={() => {
                setShowAddForm(false);
                setNewForm(EMPTY_FORM);
              }}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : messages.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          No recurring messages found.
        </div>
      ) : (
        <div className="space-y-4">
          {messages.map((message) => {
            const sectionName = sections.find((section) => section.Id === message.Section_Id)?.Name ?? 'Unknown section';
            const cadenceLabel = getCadenceLabel({
              Recurrence_Type: message.Recurrence_Type,
              Recurrence_Interval: message.Recurrence_Interval,
              Start_Date: message.Start_Date,
              End_Date: message.End_Date ?? '',
            });
            return (
              <div
                key={message.Id}
                className={`bg-white rounded-lg shadow ${!message.Is_Active ? 'opacity-70' : ''}`}
              >
                <div className="px-4 py-3 border-b border-gray-100 flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-semibold text-gray-900">{message.Headline}</h3>
                      <span className="inline-flex items-center rounded-full bg-ui-clearwater-100 px-2 py-0.5 text-[11px] font-medium text-ui-clearwater-800">
                        {message.Newsletter_Type === 'tdr' ? 'TDR' : 'My UI'}
                      </span>
                      {!message.Is_Active && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-600">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {sectionName} • {cadenceLabel}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => startEdit(message)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => void handleToggleActive(message)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
                    >
                      {message.Is_Active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => void handleDelete(message.Id)}
                      className="px-3 py-1.5 text-xs font-medium rounded-md border border-red-200 text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                <div className="px-4 py-3">
                  {editingId === message.Id ? (
                    <>
                      <RecurringMessageForm
                        value={editForm}
                        sections={getSectionsForType(editForm.Newsletter_Type)}
                        onChange={setEditForm}
                      />
                      <div className="flex items-center gap-3 mt-4">
                        <button
                          onClick={() => void handleSaveEdit()}
                          className="px-4 py-2 text-sm font-medium rounded-md bg-ui-gold-600 text-white hover:bg-ui-gold-700"
                        >
                          Save Changes
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                        >
                          Cancel
                        </button>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-gray-700 whitespace-pre-line">{message.Body}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function RecurringMessageForm({
  value,
  sections,
  onChange,
}: {
  value: RecurringMessageFormState;
  sections: NewsletterSection[];
  onChange: (value: RecurringMessageFormState) => void;
}) {
  const setField = <K extends keyof RecurringMessageFormState>(
    field: K,
    fieldValue: RecurringMessageFormState[K],
  ) => {
    const nextValue = { ...value, [field]: fieldValue };
    if (field === 'Newsletter_Type') {
      nextValue.Section_Id = '';
    }
    onChange(nextValue);
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Newsletter</label>
          <select
            value={value.Newsletter_Type}
            onChange={(event) => setField('Newsletter_Type', event.target.value as NewsletterType)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="tdr">The Daily Register</option>
            <option value="myui">My UI</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Section</label>
          <select
            value={value.Section_Id}
            onChange={(event) => setField('Section_Id', event.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select a section</option>
            {sections.map((section) => (
              <option key={section.Id} value={section.Id}>
                {section.Name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Headline</label>
        <input
          type="text"
          value={value.Headline}
          onChange={(event) => setField('Headline', event.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Body</label>
        <textarea
          value={value.Body}
          onChange={(event) => setField('Body', event.target.value)}
          rows={4}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Starts</label>
          <input
            type="date"
            value={value.Start_Date}
            onChange={(event) => setField('Start_Date', event.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Cadence</label>
          <select
            value={value.Recurrence_Type}
            onChange={(event) => setField('Recurrence_Type', event.target.value as RecurrenceType)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="once">One time</option>
            <option value="weekly">Weekly</option>
            <option value="monthly_date">Monthly (same date)</option>
            <option value="monthly_nth_weekday">Monthly (same weekday pattern)</option>
            <option value="date_range">Every issue in date range</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Interval</label>
          <input
            type="number"
            min={1}
            max={12}
            value={value.Recurrence_Interval}
            onChange={(event) => setField('Recurrence_Interval', Number(event.target.value) || 1)}
            disabled={value.Recurrence_Type === 'once' || value.Recurrence_Type === 'date_range'}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-50"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ends On</label>
          <input
            type="date"
            value={value.End_Date}
            onChange={(event) => setField('End_Date', event.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      <label className="inline-flex items-center gap-2 text-sm text-gray-600">
        <input
          type="checkbox"
          checked={value.Is_Active}
          onChange={(event) => setField('Is_Active', event.target.checked)}
          className="rounded"
        />
        Active
      </label>
    </div>
  );
}
