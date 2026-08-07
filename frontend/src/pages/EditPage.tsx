import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  addScheduleRequest,
  deleteScheduleRequest,
  getSubmission,
  rescheduleScheduleOccurrence,
  skipScheduleOccurrence,
  updateSubmission,
} from '../api/submissions';
import { triggerAIEdit, listEditVersions, saveEditorFinal } from '../api/aiEdits';
import type { Submission, TargetNewsletter } from '../types/submission';
import type { AIEditResponse, EditVersion, AIFlag, TextDiff } from '../types/aiEdit';
import DiffViewer from '../components/editor/DiffViewer';
import FlagList from '../components/editor/FlagList';
import AIEditControls from '../components/editor/AIEditControls';
import HeadlineEditor from '../components/editor/HeadlineEditor';
import BodyEditor from '../components/editor/BodyEditor';
import ChangesList from '../components/editor/ChangesList';
import SideBySideView from '../components/editor/SideBySideView';
import SubmissionMeta from '../components/editor/SubmissionMeta';
import RichBody from '../components/editor/RichBody';
import LinkEditor, { type LinkEntry } from '../components/submission/LinkEditor';
import { getSubmitterRole } from '../utils/submitterRole';
import {
  buildLinkedBody,
  normalizedBodyLinks,
  prepareBodyForEditing,
} from '../utils/bodyLinks';
import { Button, SegmentedToggle, Toast, useToast } from '../components/common';

type Tab = 'original' | 'ai_edit' | 'editor';
type ViewMode = 'diff' | 'side_by_side';
type FinalizationAction = 'draft' | 'approve' | null;
type FinalEditSource = 'original' | 'ai' | 'saved' | null;

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-status-info-100 text-status-info-800',
  ai_edited: 'bg-status-edited-100 text-status-edited-800',
  in_review: 'bg-status-warning-100 text-status-warning-800',
  approved: 'bg-status-success-100 text-status-success-800',
  scheduled: 'bg-ui-clearwater-100 text-ui-clearwater-800',
  published: 'bg-status-muted-100 text-status-muted-800',
  rejected: 'bg-status-error-100 text-status-error-800',
  pending_info: 'bg-status-attention-100 text-status-attention-800',
};

export default function EditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [submission, setSubmission] = useState<Submission | null>(null);
  const [versions, setVersions] = useState<EditVersion[]>([]);
  const [aiEditResult, setAiEditResult] = useState<AIEditResponse | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('original');
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [finalizationAction, setFinalizationAction] = useState<FinalizationAction>(null);
  const [finalEditSource, setFinalEditSource] = useState<FinalEditSource>(null);
  const [editorialSaving, setEditorialSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast, showToast, dismissToast } = useToast();
  const [occurrenceActionLoading, setOccurrenceActionLoading] = useState(false);

  const [viewMode, setViewMode] = useState<ViewMode>('side_by_side');

  // Editor state
  const [editHeadline, setEditHeadline] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editLinks, setEditLinks] = useState<LinkEntry[]>([]);
  const [assignedEditor, setAssignedEditor] = useState('');
  const [editorialNotes, setEditorialNotes] = useState('');
  const isStaff = getSubmitterRole() === 'staff';

  useEffect(() => {
    if (!id) return;

    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const sub = await getSubmission(id);
        setSubmission(sub);
        setAssignedEditor(sub.Assigned_Editor || '');
        setEditorialNotes(sub.Editorial_Notes || '');

        try {
          const vers = await listEditVersions(id);
          setVersions(vers);
          const aiVersion = [...vers].reverse().find((v) => v.Version_Type === 'ai_suggested');
          const editorVersion = [...vers].reverse().find((v) => v.Version_Type === 'editor_final');
          if (editorVersion) {
            const editable = prepareBodyForEditing(editorVersion.Body, sub.Links);
            setEditHeadline(editorVersion.Headline);
            setEditBody(editable.body);
            setEditLinks(editable.links);
            setFinalEditSource('saved');
            setActiveTab('editor');
          } else if (aiVersion) {
            const editable = prepareBodyForEditing(aiVersion.Body, sub.Links);
            setEditHeadline(aiVersion.Headline);
            setEditBody(editable.body);
            setEditLinks(editable.links);
            setFinalEditSource(null);
            setActiveTab('ai_edit');
          } else {
            const editable = prepareBodyForEditing(sub.Original_Body, sub.Links);
            setEditHeadline(sub.Original_Headline);
            setEditBody(editable.body);
            setEditLinks(editable.links);
            setFinalEditSource(null);
          }
        } catch {
          const editable = prepareBodyForEditing(sub.Original_Body, sub.Links);
          setEditHeadline(sub.Original_Headline);
          setEditBody(editable.body);
          setEditLinks(editable.links);
          setFinalEditSource(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load submission');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const sub = await getSubmission(id);
      setSubmission(sub);
      setAssignedEditor(sub.Assigned_Editor || '');
      setEditorialNotes(sub.Editorial_Notes || '');

      try {
        const vers = await listEditVersions(id);
        setVersions(vers);
        // If there's an AI suggested version, pre-populate editor fields
        const aiVersion = [...vers].reverse().find((v) => v.Version_Type === 'ai_suggested');
        const editorVersion = [...vers].reverse().find((v) => v.Version_Type === 'editor_final');
        if (editorVersion) {
          const editable = prepareBodyForEditing(editorVersion.Body, sub.Links);
          setEditHeadline(editorVersion.Headline);
          setEditBody(editable.body);
          setEditLinks(editable.links);
          setFinalEditSource('saved');
          setActiveTab('editor');
        } else if (aiVersion) {
          const editable = prepareBodyForEditing(aiVersion.Body, sub.Links);
          setEditHeadline(aiVersion.Headline);
          setEditBody(editable.body);
          setEditLinks(editable.links);
          setFinalEditSource(null);
          setActiveTab('ai_edit');
        } else {
          const editable = prepareBodyForEditing(sub.Original_Body, sub.Links);
          setEditHeadline(sub.Original_Headline);
          setEditBody(editable.body);
          setEditLinks(editable.links);
          setFinalEditSource(null);
        }
      } catch {
        // No versions yet — that's fine
        const editable = prepareBodyForEditing(sub.Original_Body, sub.Links);
        setEditHeadline(sub.Original_Headline);
        setEditBody(editable.body);
        setEditLinks(editable.links);
        setFinalEditSource(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load submission');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerEdit = async (
    newsletterType: 'tdr' | 'myui',
    editorInstructions?: string,
  ) => {
    if (!id) return;
    setAiLoading(true);
    setError(null);
    try {
      const result = editorInstructions === undefined
        ? await triggerAIEdit(id, newsletterType)
        : await triggerAIEdit(id, newsletterType, editorInstructions);
      const editable = prepareBodyForEditing(
        result.Edited_Body,
        [
          ...result.Embedded_Links.map((link, index) => ({
            Url: link.url,
            Anchor_Text: link.anchor_text,
            Display_Order: index,
          })),
          ...(submission?.Links ?? []),
        ],
      );
      setAiEditResult(result);
      setEditHeadline(result.Edited_Headline);
      setEditBody(editable.body);
      setEditLinks(editable.links);
      setFinalEditSource(null);
      setActiveTab('ai_edit');
      // Refresh data
      const sub = await getSubmission(id);
      setSubmission(sub);
      const vers = await listEditVersions(id);
      setVersions(vers);
      showToast(editorInstructions ? 'AI revision complete' : 'AI edit complete');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'AI edit failed';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setAiLoading(false);
    }
  };

  const handleReviewFinalEdit = (source: 'original' | 'ai') => {
    if (!submission) return;
    if (source === 'original') {
      const editable = prepareBodyForEditing(submission.Original_Body, submission.Links);
      setEditHeadline(submission.Original_Headline);
      setEditBody(editable.body);
      setEditLinks(editable.links);
    } else {
      const aiVersion = [...versions].reverse().find((v) => v.Version_Type === 'ai_suggested');
      const headline = aiVersion?.Headline || aiEditResult?.Edited_Headline;
      const body = aiVersion?.Body || aiEditResult?.Edited_Body;
      if (!headline || !body) {
        setError('No AI suggestion is available for final editing.');
        return;
      }
      const editable = prepareBodyForEditing(body, submission.Links);
      setEditHeadline(headline);
      setEditBody(editable.body);
      setEditLinks(editable.links);
    }
    setFinalEditSource(source);
    setActiveTab('editor');
  };

  const handleFinalize = async (approveForNewsletter: boolean) => {
    if (!id) return;
    setFinalizationAction(approveForNewsletter ? 'approve' : 'draft');
    setError(null);
    try {
      const aiVersion = [...versions].reverse().find((v) => v.Version_Type === 'ai_suggested');
      const editorVersion = [...versions].reverse().find((v) => v.Version_Type === 'editor_final');
      const sourceVersion = finalEditSource === 'ai'
        ? aiVersion
        : finalEditSource === 'saved'
          ? editorVersion
          : undefined;
      const links = normalizedBodyLinks(editLinks);
      await saveEditorFinal(id, {
        Headline: editHeadline,
        Body: buildLinkedBody(editBody, links),
        Headline_Case: sourceVersion?.Headline_Case || undefined,
        Approve_For_Newsletter: approveForNewsletter,
        ...((submission?.Links.length ?? 0) > 0 || links.length > 0
          ? { Links: links }
          : {}),
      });
      showToast(
        approveForNewsletter
          ? 'Final version saved and approved for newsletter'
          : 'Draft saved. Submission remains in review',
      );
      await loadData();
    } catch (err) {
      const message = err instanceof Error
        ? err.message
        : approveForNewsletter
          ? 'Failed to save and approve'
          : 'Failed to save draft';
      setError(message);
      showToast(message, 'error');
    } finally {
      setFinalizationAction(null);
    }
  };

  const handleSaveEditorialWorkflow = async () => {
    if (!id || !isStaff) return;
    setEditorialSaving(true);
    try {
      const updated = await updateSubmission(id, {
        Assigned_Editor: assignedEditor.trim() || null,
        Editorial_Notes: editorialNotes.trim() || null,
      } as Partial<Submission>);
      setSubmission(updated);
      setAssignedEditor(updated.Assigned_Editor || '');
      setEditorialNotes(updated.Editorial_Notes || '');
      showToast('Editorial workflow details saved');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save editorial workflow details';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setEditorialSaving(false);
    }
  };

  const [showPendingConfirm, setShowPendingConfirm] = useState(false);

  const handleRequestInfo = () => {
    if (!id || !submission) return;
    const newsletterName =
      submission.Target_Newsletter === 'tdr'
        ? 'The Daily Register'
        : submission.Target_Newsletter === 'myui'
          ? 'My UI'
          : 'The Daily Register / My UI';

    const subject = encodeURIComponent(
      `More information needed: ${submission.Original_Headline}`,
    );
    const body = encodeURIComponent(
      `Hi ${submission.Submitter_Name},\n\n` +
        `Thank you for your submission to ${newsletterName}: "${submission.Original_Headline}"\n\n` +
        `We need some additional information before we can include it in the newsletter. Could you please provide:\n\n` +
        `- \n\n` +
        `Please reply to this email with the details at your earliest convenience.\n\n` +
        `Thank you,\nUniversity Communications and Marketing`,
    );

    window.location.href = `mailto:${submission.Submitter_Email}?subject=${subject}&body=${body}`;

    // Show confirmation prompt instead of auto-setting pending_info
    setShowPendingConfirm(true);
  };

  const handleConfirmPendingInfo = async () => {
    if (!id) return;
    setShowPendingConfirm(false);
    try {
      await updateSubmission(id, { Status: 'pending_info' } as Partial<Submission>);
      showToast('Status updated to Pending Info');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const handleClearPendingInfo = async () => {
    if (!id) return;
    try {
      await updateSubmission(id, { Status: 'in_review' } as Partial<Submission>);
      showToast('Status changed back to In Review');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const handleChangeNewsletter = async (target: TargetNewsletter) => {
    if (!id) return;
    try {
      await updateSubmission(id, { Target_Newsletter: target } as Partial<Submission>);
      showToast(`Newsletter changed to ${target === 'tdr' ? 'Daily Register' : target === 'myui' ? 'My UI' : 'Both'}`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change newsletter');
    }
  };

  const handleSkipOccurrence = async (scheduleId: string, occurrenceDate: string) => {
    if (!id) return;
    setOccurrenceActionLoading(true);
    try {
      await skipScheduleOccurrence(id, scheduleId, occurrenceDate);
      showToast(`Skipped occurrence on ${new Date(`${occurrenceDate}T12:00:00`).toLocaleDateString()}`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip occurrence');
    } finally {
      setOccurrenceActionLoading(false);
    }
  };

  const handleRescheduleOccurrence = async (
    scheduleId: string,
    occurrenceDate: string,
    newDate: string,
  ) => {
    if (!id) return;
    setOccurrenceActionLoading(true);
    try {
      await rescheduleScheduleOccurrence(id, scheduleId, occurrenceDate, newDate);
      showToast(
        `Moved ${new Date(`${occurrenceDate}T12:00:00`).toLocaleDateString()} to ${new Date(`${newDate}T12:00:00`).toLocaleDateString()}`,
      );
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to move occurrence');
    } finally {
      setOccurrenceActionLoading(false);
    }
  };

  const handleAddScheduleDate = async (
    newsletter: string,
    date: string,
    recurrence?: {
      Recurrence_Type: 'weekly' | 'monthly_date' | 'monthly_nth_weekday';
      Recurrence_Interval: number;
      Recurrence_End_Date?: string;
    },
  ) => {
    if (!id) return;
    await addScheduleRequest(id, { Requested_Date: date, ...(recurrence ?? {}) });
    const dateLabel = new Date(`${date}T12:00:00`).toLocaleDateString();
    const newsletterLabel = newsletter === 'tdr' ? 'Daily Register' : 'My UI';
    showToast(
      recurrence
        ? `Added recurring run date starting ${dateLabel} for ${newsletterLabel}`
        : `Added run date ${dateLabel} for ${newsletterLabel}`,
    );
    await loadData();
  };

  const handleRemoveScheduleRequest = async (scheduleId: string) => {
    if (!id) return;
    await deleteScheduleRequest(id, scheduleId);
    showToast('Removed run date schedule');
    await loadData();
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading submission...</div>;
  }

  if (error && !submission) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="text-sm text-ui-gold-600 hover:text-ui-gold-700"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  if (!submission) return null;

  const aiVersion = [...versions].reverse().find((v) => v.Version_Type === 'ai_suggested');
  const hasAIEdit = !!aiVersion || !!aiEditResult;

  // Build diff data from aiEditResult or reconstruct from versions
  const headlineDiff: TextDiff | null = aiEditResult?.Headline_Diff || null;
  const bodyDiff: TextDiff | null = aiEditResult?.Body_Diff || null;
  const flags: AIFlag[] = aiEditResult?.Flags || aiVersion?.Flags || [];
  const changesMade: string[] = aiEditResult?.Changes_Made || aiVersion?.Changes_Made || [];
  const confidence = aiEditResult?.Confidence;
  const canApproveFinal = ['new', 'ai_edited', 'in_review', 'approved'].includes(
    submission.Status,
  );

  const tabs: { id: Tab; label: string; available: boolean }[] = [
    { id: 'original', label: 'Original', available: true },
    { id: 'ai_edit', label: 'AI Suggested', available: hasAIEdit },
    { id: 'editor', label: 'Final Edit', available: true },
  ];
  const finalEditSourceLabel = finalEditSource === 'ai'
    ? 'AI suggestion'
    : finalEditSource === 'saved'
      ? 'Saved final version'
      : 'Original submission';

  const handleTabChange = (tab: Tab) => {
    const selected = tabs.find((candidate) => candidate.id === tab);
    if (!selected?.available) return;
    if (tab !== 'editor' || activeTab === 'editor') {
      setActiveTab(tab);
      return;
    }
    if (finalEditSource !== null) {
      setActiveTab('editor');
      return;
    }
    handleReviewFinalEdit(activeTab === 'ai_edit' ? 'ai' : 'original');
  };

  return (
    <div>
      <Toast toast={toast} onDismiss={dismissToast} />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-400 hover:text-gray-600"
          >
            &larr;
          </button>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Edit Submission</h2>
            <p className="text-xs text-gray-500">ID: {submission.Id}</p>
          </div>
        </div>
        <span
          className={`text-xs px-3 py-1 rounded-full font-medium ${STATUS_COLORS[submission.Status] || 'bg-gray-100'}`}
        >
          {submission.Status.replace('_', ' ')}
        </span>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-4 text-red-400 hover:text-red-600"
          >
            &times;
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main content area — 3 cols */}
        <div className="lg:col-span-3">
          {/* Tabs */}
          <div className="border-b border-gray-200 mb-4">
            <nav className="flex gap-4">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  disabled={!tab.available}
                  className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-ui-gold-500 text-ui-gold-600'
                      : tab.available
                        ? 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        : 'border-transparent text-gray-300 cursor-not-allowed'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          <div className="bg-white rounded-lg shadow p-6">
            {activeTab === 'original' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Original Headline
                  </label>
                  <p className="text-sm font-medium text-gray-900 bg-gray-50 p-3 rounded">
                    {submission.Original_Headline}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Original Body
                  </label>
                  <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded whitespace-pre-wrap">
                    {submission.Original_Body}
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'ai_edit' && hasAIEdit && (
              <div className="space-y-6">
                {/* View mode toggle */}
                <SegmentedToggle
                  ariaLabel="AI edit view"
                  value={viewMode}
                  onChange={setViewMode}
                  options={[
                    { value: 'side_by_side', label: 'Side by Side' },
                    { value: 'diff', label: 'Inline Diff' },
                  ]}
                />

                {/* Inline diff mode */}
                {viewMode === 'diff' && (
                  <>
                    {headlineDiff && (
                      <DiffViewer diff={headlineDiff} label="Headline Changes" />
                    )}
                    {!headlineDiff && aiVersion && (
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                          AI Headline
                        </label>
                        <p className="text-sm font-medium text-emerald-900 bg-green-50 p-3 rounded">
                          {aiVersion.Headline}
                        </p>
                      </div>
                    )}

                    {bodyDiff && <DiffViewer diff={bodyDiff} label="Body Changes" />}
                    {!bodyDiff && aiVersion && (
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">
                          AI Body
                        </label>
                        <RichBody text={aiVersion.Body} className="text-sm text-emerald-800 bg-green-50 p-3 rounded" />
                      </div>
                    )}
                  </>
                )}

                {/* Side-by-side mode */}
                {viewMode === 'side_by_side' && (
                  <SideBySideView
                    originalHeadline={submission.Original_Headline}
                    originalBody={submission.Original_Body}
                    aiHeadline={aiVersion?.Headline || aiEditResult?.Edited_Headline || ''}
                    aiBody={aiVersion?.Body || aiEditResult?.Edited_Body || ''}
                  />
                )}

                {/* Flags */}
                {flags.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                      Flags ({flags.length})
                    </h4>
                    <FlagList flags={flags} />
                  </div>
                )}

                {/* Changes made */}
                {changesMade.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                      Changes Made
                    </h4>
                    <ChangesList changes={changesMade} />
                  </div>
                )}
              </div>
            )}

            {activeTab === 'editor' && (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                <section
                  aria-label="Original submission"
                  className="space-y-4 rounded-lg border border-gray-200 bg-gray-50 p-4 lg:sticky lg:top-6 lg:self-start"
                >
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">Original submission</h3>
                    <p className="mt-1 text-xs text-gray-500">Read-only reference</p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium text-gray-500">Headline</p>
                    <p className="text-sm font-medium text-gray-900">
                      {submission.Original_Headline}
                    </p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-medium text-gray-500">Body</p>
                    <p className="whitespace-pre-wrap text-sm leading-6 text-gray-700">
                      {submission.Original_Body}
                    </p>
                  </div>
                  {submission.Links.length > 0 && (
                    <div>
                      <p className="mb-1 text-xs font-medium text-gray-500">Submitted links</p>
                      <ul className="space-y-1">
                        {[...submission.Links]
                          .sort((a, b) => a.Display_Order - b.Display_Order)
                          .map((link) => (
                            <li key={link.Id} className="text-sm text-gray-700">
                              {link.Anchor_Text?.trim() && (
                                <span className="font-medium">{link.Anchor_Text} — </span>
                              )}
                              <span className="break-all text-gray-500">{link.Url}</span>
                            </li>
                          ))}
                      </ul>
                    </div>
                  )}
                </section>

                <section aria-label="Final edit" className="min-w-0 space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">Final edit</h3>
                    <p className="mt-1 text-xs text-gray-500">
                      Starting point: {finalEditSourceLabel}
                    </p>
                  </div>
                  <HeadlineEditor
                    value={editHeadline}
                    onChange={setEditHeadline}
                    headlineCase={aiVersion?.Headline_Case || null}
                  />
                  <BodyEditor value={editBody} onChange={setEditBody} />
                  <div className="border-t border-gray-100 pt-4">
                    <LinkEditor
                      links={editLinks}
                      onChange={setEditLinks}
                      label="Links and CTA text"
                      description="Link text stays readable in the body while its destination is edited here. Add a secure web URL or an email address."
                    />
                  </div>
                  {editLinks.some((link) => link.Url.trim()) && (
                    <section
                      aria-label="Newsletter body preview"
                      className="rounded-md border border-gray-200 bg-gray-50 px-4 py-3"
                    >
                      <p className="mb-2 text-xs font-medium text-gray-500">Live preview</p>
                      <RichBody
                        text={buildLinkedBody(editBody, editLinks)}
                        className="text-sm leading-6 text-gray-800"
                      />
                    </section>
                  )}
                  <div className="flex flex-col gap-3 border-t border-gray-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {canApproveFinal
                          ? 'Ready for newsletter assembly?'
                          : 'Save your work before leaving'}
                      </p>
                      <p className="mt-0.5 max-w-[65ch] text-xs text-gray-500">
                        {canApproveFinal
                          ? 'Save a draft for continued review, or approve the current text for the newsletter.'
                          : 'This submission cannot be approved in its current status, but you can keep your edits as a draft.'}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-wrap justify-end gap-2">
                      <Button
                        onClick={() => void handleFinalize(false)}
                        disabled={finalizationAction !== null}
                        variant="secondary"
                      >
                        {finalizationAction === 'draft' ? 'Saving draft...' : 'Save Draft'}
                      </Button>
                      {canApproveFinal && (
                        <Button
                          onClick={() => void handleFinalize(true)}
                          disabled={finalizationAction !== null}
                          variant="success"
                          title="Save this final version and approve it for newsletter assembly"
                        >
                          {finalizationAction === 'approve'
                            ? 'Saving and approving...'
                            : 'Save and Approve'}
                        </Button>
                      )}
                    </div>
                  </div>
                </section>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar — 1 col */}
        <div className="space-y-4">
          <AIEditControls
            onTriggerEdit={handleTriggerEdit}
            onReviewFinalEdit={handleReviewFinalEdit}
            loading={aiLoading}
            hasAIEdit={hasAIEdit}
            targetNewsletter={submission.Target_Newsletter}
            confidence={confidence}
            reviewSource={activeTab === 'ai_edit' ? 'ai' : activeTab === 'original' ? 'original' : null}
          />
          <SubmissionMeta
            submission={submission}
            onChangeNewsletter={handleChangeNewsletter}
            onSkipOccurrence={isStaff ? handleSkipOccurrence : undefined}
            onRescheduleOccurrence={isStaff ? handleRescheduleOccurrence : undefined}
            onAddScheduleDate={isStaff ? handleAddScheduleDate : undefined}
            onRemoveScheduleRequest={isStaff ? handleRemoveScheduleRequest : undefined}
            occurrenceActionLoading={isStaff ? occurrenceActionLoading : false}
          />

          {isStaff && (
            <div className="bg-white rounded-lg border p-4 space-y-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Editorial Workflow</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Track who owns this item and any internal editorial context.
                </p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Assigned Editor
                </label>
                <input
                  type="text"
                  value={assignedEditor}
                  onChange={(e) => setAssignedEditor(e.target.value)}
                  placeholder="e.g., Jane Smith"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Internal Notes
                </label>
                <textarea
                  value={editorialNotes}
                  onChange={(e) => setEditorialNotes(e.target.value)}
                  rows={5}
                  placeholder="Internal handoff notes, follow-up items, source context, or pending questions."
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
              </div>
              <Button
                onClick={handleSaveEditorialWorkflow}
                disabled={editorialSaving}
                className="w-full bg-ui-clearwater-600 hover:bg-ui-clearwater-700"
              >
                {editorialSaving ? 'Saving...' : 'Save Workflow Details'}
              </Button>
            </div>
          )}

          {/* Request More Info / Pending Info controls */}
          {submission.Status === 'pending_info' ? (
            <Button
              onClick={handleClearPendingInfo}
              variant="success"
              className="w-full bg-status-success-100 text-status-success-800 hover:bg-status-success-100"
            >
              Mark Info Received
            </Button>
          ) : (
            <Button
              onClick={handleRequestInfo}
              className="w-full border border-status-attention-100 bg-status-attention-100 text-status-attention-800 hover:bg-status-attention-100"
            >
              Request More Info
            </Button>
          )}

          {/* Confirmation prompt after mailto opens */}
          {showPendingConfirm && (
            <div className="bg-orange-50 border border-orange-200 rounded-md p-3 text-sm space-y-2">
              <p className="text-orange-800">Did you send the email?</p>
              <div className="flex gap-2">
                <Button
                  onClick={handleConfirmPendingInfo}
                  size="sm"
                  className="flex-1 bg-status-attention-500 text-white hover:bg-status-attention-800"
                >
                  Yes, mark pending
                </Button>
                <Button
                  onClick={() => setShowPendingConfirm(false)}
                  variant="secondary"
                  size="sm"
                  className="flex-1"
                >
                  No, cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
