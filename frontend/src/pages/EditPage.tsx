import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  addScheduleRequest,
  deleteScheduleRequest,
  getSubmission,
  rescheduleScheduleOccurrence,
  skipScheduleOccurrence,
  updateScheduleRequestEnding,
  updateSubmission,
} from '../api/submissions';
import { triggerAIEdit, listEditVersions, saveEditorFinal } from '../api/aiEdits';
import { ApiError } from '../api/client';
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
import type { ScheduleEnding } from '../components/editor/ScheduleEndingEditor';
import OriginalSubmissionFields from '../components/editor/OriginalSubmissionFields';
import RichBody from '../components/editor/RichBody';
import LinkEditor, { type LinkEntry } from '../components/submission/LinkEditor';
import { getSubmitterRole } from '../utils/submitterRole';
import {
  buildLinkedBody,
  commitLinkLabel,
  normalizedBodyLinks,
  prepareBodyForEditing,
  synchronizeLinksWithBodyChange,
  EDITOR_MAX_LINKS,
  linkSaveProblem,
} from '../utils/bodyLinks';
import { buildEditorScheduleRequest } from '../utils/editorSchedule';
import { Button, SegmentedToggle, Toast, useToast } from '../components/common';
import useConfirmAction from '../components/common/useConfirmAction';

type Tab = 'original' | 'ai_edit' | 'editor';
type ViewMode = 'diff' | 'side_by_side' | 'live';
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

interface SaveConflict {
  approve: boolean;
  current: { Id: string; Headline: string; Body: string; Approved: boolean } | null;
}

/** The 409 the backend returns when a save was based on an older staff revision. */
function saveConflictFrom(err: unknown, approve: boolean): SaveConflict | null {
  if (!(err instanceof ApiError) || err.status !== 409) return null;
  const detail = err.detail as { Current_Revision?: SaveConflict['current'] } | null;
  if (!detail || typeof detail !== 'object' || !('Current_Revision' in detail)) return null;
  return { approve, current: detail.Current_Revision ?? null };
}

/** Compares editor text with what was loaded, to tell whether staff changed it. */
function editorTextKey(headline: string, body: string, links: LinkEntry[]): string {
  return JSON.stringify([headline, body, links]);
}

/** The version the backend names as the submission's working revision. */
function workingVersion(versions: EditVersion[], submission: Submission): EditVersion | undefined {
  return versions.find((v) => v.Id === submission.Working_Version_Id);
}

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
  const [saveConflict, setSaveConflict] = useState<SaveConflict | null>(null);
  const { toast, showToast, dismissToast } = useToast();
  const [occurrenceActionLoading, setOccurrenceActionLoading] = useState(false);

  const [viewMode, setViewMode] = useState<ViewMode>('side_by_side');

  // Editor state
  const [editHeadline, setEditHeadline] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editLinks, setEditLinks] = useState<LinkEntry[]>([]);
  // The editor text as it was last loaded. Once staff change it, the editor
  // is dirty: an AI result or a "Use ... in Final Edit" button never replaces
  // that text without asking (#511).
  const editorSeedRef = useRef(editorTextKey('', '', []));
  const editorSnapshot = editorTextKey(editHeadline, editBody, editLinks);
  const editorSnapshotRef = useRef(editorSnapshot);
  useEffect(() => {
    editorSnapshotRef.current = editorSnapshot;
  }, [editorSnapshot]);
  // An AI result arrived while the editor held unsaved text, so the editor
  // does not hold the latest suggestion even when it started from an older one.
  const [newerAiSuggestion, setNewerAiSuggestion] = useState(false);
  const seedEditor = (headline: string, editable: { body: string; links: LinkEntry[] }) => {
    setEditHeadline(headline);
    setEditBody(editable.body);
    setEditLinks(editable.links);
    editorSeedRef.current = editorTextKey(headline, editable.body, editable.links);
    setNewerAiSuggestion(false);
  };
  // Reads refs, so an AI request that finishes later sees the current text.
  const isEditorDirty = () => editorSnapshotRef.current !== editorSeedRef.current;
  const { requestConfirmation, confirmationDialog } = useConfirmAction();
  // The staff revision the editor text was loaded from. A sidebar refresh can
  // bring in a newer Staff_Revision_Id without the text that goes with it, so
  // saves are checked against this one, never the refreshed submission's.
  const [editBaseRevisionId, setEditBaseRevisionId] = useState<string | null>(null);
  const [assignedEditor, setAssignedEditor] = useState('');
  const [editorialNotes, setEditorialNotes] = useState('');
  const isStaff = getSubmitterRole() === 'staff';

  const loadData = useCallback(async (preserveAILiveView = false) => {
    if (!id) return;
    const seed = (headline: string, editable: { body: string; links: LinkEntry[] }) => {
      setEditHeadline(headline);
      setEditBody(editable.body);
      setEditLinks(editable.links);
      editorSeedRef.current = editorTextKey(headline, editable.body, editable.links);
      setNewerAiSuggestion(false);
    };
    setLoading(true);
    setError(null);
    try {
      const sub = await getSubmission(id);
      setSubmission(sub);
      setAssignedEditor(sub.Assigned_Editor || '');
      setEditorialNotes(sub.Editorial_Notes || '');
      setEditBaseRevisionId(sub.Staff_Revision_Id ?? null);

      try {
        const vers = await listEditVersions(id);
        setVersions(vers);
        // Open the revision the backend names as authoritative; never pick
        // one here by timestamp (see editorial_content.working_revision).
        const working = workingVersion(vers, sub);
        if (working?.Version_Type === 'editor_final') {
          seed(working.Headline, prepareBodyForEditing(working.Body, sub.Links));
          setFinalEditSource('saved');
          setActiveTab(preserveAILiveView ? 'ai_edit' : 'editor');
        } else if (working?.Version_Type === 'ai_suggested') {
          seed(working.Headline, prepareBodyForEditing(working.Body, sub.Links));
          setFinalEditSource(null);
          setActiveTab('ai_edit');
        } else {
          seed(sub.Original_Headline, prepareBodyForEditing(sub.Original_Body, sub.Links));
          setFinalEditSource(null);
        }
      } catch {
        // No versions yet — that's fine
        seed(sub.Original_Headline, prepareBodyForEditing(sub.Original_Body, sub.Links));
        setFinalEditSource(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load submission');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  /**
   * Re-read the submission after a sidebar action (status, newsletter, run
   * dates). Those actions never change the text, so the editor's unsaved
   * headline, body, links and workflow notes stay as they are (#489).
   */
  const refreshSubmission = useCallback(async () => {
    if (!id) return;
    try {
      setSubmission(await getSubmission(id));
    } catch (err) {
      // The action itself succeeded; only the re-read failed.
      setError(err instanceof Error ? err.message : 'Failed to reload submission');
    }
  }, [id]);

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
      // Staff may have typed in Final Edit before asking for a revision, or
      // while the AI ran. Keep that text; the result stays on the AI
      // Suggested tab, and "Use AI Suggestion in Final Edit" asks first (#511).
      const keptEdits = isEditorDirty();
      if (keptEdits) {
        setViewMode((mode) => (mode === 'live' ? 'side_by_side' : mode));
        setNewerAiSuggestion(true);
      } else {
        seedEditor(result.Edited_Headline, editable);
        setFinalEditSource(null);
      }
      setActiveTab('ai_edit');
      // Refresh data. Text loaded from the AI result starts from the current
      // revision; kept text stays on the revision it was loaded from.
      const sub = await getSubmission(id);
      setSubmission(sub);
      if (!keptEdits) setEditBaseRevisionId(sub.Staff_Revision_Id ?? null);
      const vers = await listEditVersions(id);
      setVersions(vers);
      const done = editorInstructions ? 'AI revision complete' : 'AI edit complete';
      showToast(keptEdits
        ? `${done}. Your unsaved Final Edit changes were kept. Use AI Suggestion in Final Edit to replace them.`
        : done);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'AI edit failed';
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setAiLoading(false);
    }
  };

  const loadFinalEdit = (source: 'original' | 'ai') => {
    if (!submission) return;
    if (source === 'original') {
      seedEditor(
        submission.Original_Headline,
        prepareBodyForEditing(submission.Original_Body, submission.Links),
      );
    } else if (finalEditSource !== 'ai' || newerAiSuggestion) {
      const aiVersion = [...versions].reverse().find((v) => v.Version_Type === 'ai_suggested');
      const headline = aiVersion?.Headline || aiEditResult?.Edited_Headline;
      const body = aiVersion?.Body || aiEditResult?.Edited_Body;
      const headlineRequired = submission.Category !== 'job_opportunity';
      if (!body || (headlineRequired && !headline)) {
        setError('No AI suggestion is available for final editing.');
        return;
      }
      seedEditor(headline || '', prepareBodyForEditing(body, submission.Links));
    }
    setFinalEditSource(source);
    setActiveTab('editor');
  };

  const handleReviewFinalEdit = (source: 'original' | 'ai') => {
    if (!submission) return;
    // Changes made in Live View are edits of the AI suggestion; carrying them
    // into Final Edit replaces nothing.
    const replacesText = source === 'original' || finalEditSource !== 'ai' || newerAiSuggestion;
    if (!replacesText || !isEditorDirty()) {
      loadFinalEdit(source);
      return;
    }
    const label = source === 'original' ? 'the original submission' : 'the AI suggestion';
    requestConfirmation({
      title: 'Replace your Final Edit changes?',
      description: `Final Edit has changes that are not saved. Replacing them with ${label} discards those changes. `
        + 'Cancel and use Save Draft first to keep them.',
      confirmLabel: 'Replace changes',
      action: async () => loadFinalEdit(source),
    });
  };

  const handleEditBodyChange = (nextBody: string) => {
    setEditBody(nextBody);
  };

  const handleEditBodyCommit = (previousBody: string, nextBody: string) => {
    setEditLinks((links) => synchronizeLinksWithBodyChange(
      previousBody,
      nextBody,
      links,
    ));
  };

  const handleLinkAnchorCommit = (
    index: number,
    previousValue: string,
    nextValue: string,
  ) => {
    const link = editLinks[index] ?? { Url: '', Anchor_Text: '' };
    const result = commitLinkLabel(editBody, { ...link, Anchor_Text: previousValue }, nextValue);
    setEditBody(result.body);
    setEditLinks((links) => links.map((candidate, candidateIndex) => (
      candidateIndex === index ? { ...candidate, Start: result.link.Start } : candidate
    )));
  };

  // Put a link's missing words back at the end of the body (#397).
  const handleLinkWordsRestore = (index: number) => {
    handleLinkAnchorCommit(index, '', editLinks[index]?.Anchor_Text ?? '');
  };

  const handleLinkMentionChange = (index: number, start: number) => {
    setEditLinks((links) => links.map((link, linkIndex) => (
      linkIndex === index ? { ...link, Start: start } : link
    )));
  };

  const handleFinalize = async (approveForNewsletter: boolean, baseOverride?: string | null) => {
    if (!id) return;
    // Saving would otherwise silently drop these links and their destinations.
    const linkProblem = linkSaveProblem(editBody, editLinks);
    if (linkProblem) {
      setError(linkProblem);
      return;
    }
    setFinalizationAction(approveForNewsletter ? 'approve' : 'draft');
    setError(null);
    try {
      const aiVersion = [...versions].reverse().find((v) => v.Version_Type === 'ai_suggested');
      const sourceVersion = finalEditSource === 'ai'
        ? aiVersion
        : finalEditSource === 'saved' && submission
          ? workingVersion(versions, submission)
          : undefined;
      const links = normalizedBodyLinks(editLinks, editBody);
      await saveEditorFinal(id, {
        Headline: submission?.Category === 'job_opportunity' ? '' : editHeadline,
        Body: buildLinkedBody(editBody, links),
        Headline_Case: sourceVersion?.Headline_Case || undefined,
        Approve_For_Newsletter: approveForNewsletter,
        // The staff revision this view was based on; a newer save makes this a conflict.
        Base_Staff_Revision_Id: baseOverride !== undefined
          ? baseOverride
          : editBaseRevisionId,
        // Start is editor state; the saved body already records each link's place.
        ...((submission?.Links.length ?? 0) > 0 || links.length > 0
          ? {
            Links: links.map(({ Url, Anchor_Text, Display_Order }) => ({
              Url,
              Anchor_Text,
              Display_Order,
            })),
          }
          : {}),
      });
      setSaveConflict(null);
      showToast(
        approveForNewsletter
          ? 'Final version saved and approved for newsletter'
          : 'Draft saved. Submission remains in review',
      );
      await loadData(activeTab === 'ai_edit' && viewMode === 'live');
    } catch (err) {
      const conflict = saveConflictFrom(err, approveForNewsletter);
      if (conflict) {
        // Keep the editor's unsaved text in place so it can be compared.
        setSaveConflict(conflict);
        return;
      }
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
      await refreshSubmission();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const handleClearPendingInfo = async () => {
    if (!id) return;
    try {
      await updateSubmission(id, { Status: 'in_review' } as Partial<Submission>);
      showToast('Status changed back to In Review');
      await refreshSubmission();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const handleChangeNewsletter = async (target: TargetNewsletter) => {
    if (!id) return;
    try {
      await updateSubmission(id, { Target_Newsletter: target } as Partial<Submission>);
      showToast(`Newsletter changed to ${target === 'tdr' ? 'Daily Register' : target === 'myui' ? 'My UI' : 'Both'}`);
      await refreshSubmission();
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
      await refreshSubmission();
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
      await refreshSubmission();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to move occurrence');
    } finally {
      setOccurrenceActionLoading(false);
    }
  };

  const handleAddScheduleDate = async (
    newsletter: 'tdr' | 'myui',
    date: string,
    recurrence?: {
      Recurrence_Type: 'weekly' | 'monthly_date' | 'monthly_nth_weekday';
      Recurrence_Interval: number;
      Recurrence_End_Date?: string;
      Repeats_Indefinitely?: boolean;
    },
  ) => {
    if (!id || !submission) return;
    await addScheduleRequest(
      id,
      buildEditorScheduleRequest(
        submission.Target_Newsletter,
        newsletter,
        date,
        recurrence,
      ),
    );
    const dateLabel = new Date(`${date}T12:00:00`).toLocaleDateString();
    const newsletterLabel = newsletter === 'tdr' ? 'Daily Register' : 'My UI';
    showToast(
      recurrence
        ? `Added recurring run date starting ${dateLabel} for ${newsletterLabel}`
        : `Added run date ${dateLabel} for ${newsletterLabel}`,
    );
    await refreshSubmission();
  };

  const handleUpdateScheduleEnding = async (scheduleId: string, ending: ScheduleEnding) => {
    if (!id) return;
    await updateScheduleRequestEnding(id, scheduleId, ending);
    showToast(
      ending.Repeats_Indefinitely
        ? 'Schedule set to repeat indefinitely'
        : `Schedule ends ${new Date(`${ending.Recurrence_End_Date}T12:00:00`).toLocaleDateString()}`,
    );
    await refreshSubmission();
  };

  const handleRemoveScheduleRequest = async (scheduleId: string) => {
    if (!id) return;
    await deleteScheduleRequest(id, scheduleId);
    showToast('Removed run date schedule');
    await refreshSubmission();
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading submission...</div>;
  }

  if (error && !submission) {
    return (
      <div className="text-center py-12">
        <p className="text-status-error-800 mb-4">{error}</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="text-sm text-ui-gold-800 hover:text-ui-gold-800"
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
  const isJobSubmission = submission.Category === 'job_opportunity';

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

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    // Live View edits the current working copy; never overwrite a saved draft
    // or in-progress Final Edit content with the AI suggestion.
    if (mode === 'live' && finalEditSource === null) {
      setFinalEditSource('ai');
    }
  };

  const editingFields = (
    <>
      {isJobSubmission ? (
        <div className="rounded-md border border-ui-gold-200 bg-ui-gold-50 px-3 py-2">
          <p className="text-xs font-medium text-ui-gold-800">Jobs listing</p>
          <p className="mt-0.5 text-xs text-ui-gold-800">
            Jobs run as one linked line without a separate headline.
          </p>
        </div>
      ) : (
        <HeadlineEditor
          value={editHeadline}
          onChange={setEditHeadline}
          headlineCase={aiVersion?.Headline_Case || null}
        />
      )}
      <BodyEditor
        value={editBody}
        onChange={handleEditBodyChange}
        onCommit={handleEditBodyCommit}
      />
      <div className="border-t border-gray-100 pt-4">
        <LinkEditor
          links={editLinks}
          onChange={setEditLinks}
          onAnchorCommit={handleLinkAnchorCommit}
          body={editBody}
          onMentionChange={handleLinkMentionChange}
          onRestoreWords={handleLinkWordsRestore}
          allowAddRemove
          maxLinks={EDITOR_MAX_LINKS}
          label="Links and CTA text"
          description="Link text stays readable in the body while its destination is edited here. Add a secure web URL (https://) or an email address."
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
    </>
  );

  const handleDiscardForNewerVersion = async () => {
    setSaveConflict(null);
    await loadData(activeTab === 'ai_edit' && viewMode === 'live');
  };

  const conflictPanel = saveConflict && (
    <section
      aria-label="Save conflict"
      className="rounded-md border border-status-warning-500/50 bg-status-warning-100/60 p-4"
    >
      <p className="text-sm font-medium text-status-warning-800">
        Someone saved a newer version while you were editing. Nothing was saved.
      </p>
      <p className="mt-1 text-xs text-gray-600">
        Compare it with your text below, then keep theirs or save yours over it.
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">
            {saveConflict.current?.Approved ? 'Newer saved version (approved)' : 'Newer saved version'}
          </p>
          {saveConflict.current ? (
            <>
              {saveConflict.current.Headline && (
                <p className="mt-1 text-sm font-medium text-gray-900">{saveConflict.current.Headline}</p>
              )}
              <RichBody text={saveConflict.current.Body} className="mt-1 text-sm leading-6 text-gray-800" />
            </>
          ) : (
            <p className="mt-1 text-sm text-gray-600">Reload to see the current version.</p>
          )}
        </div>
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500">Your unsaved text</p>
          {editHeadline && <p className="mt-1 text-sm font-medium text-gray-900">{editHeadline}</p>}
          <RichBody
            text={buildLinkedBody(editBody, editLinks)}
            className="mt-1 text-sm leading-6 text-gray-800"
          />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          variant="secondary"
          onClick={handleDiscardForNewerVersion}
          disabled={finalizationAction !== null}
        >
          Discard mine and load theirs
        </Button>
        {saveConflict.current && (
          <Button
            onClick={() => handleFinalize(saveConflict.approve, saveConflict.current?.Id ?? null)}
            disabled={finalizationAction !== null}
          >
            {saveConflict.approve ? 'Save and approve mine instead' : 'Save mine instead'}
          </Button>
        )}
      </div>
    </section>
  );

  const finalizationControls = (
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
  );

  return (
    <div>
      <Toast toast={toast} onDismiss={dismissToast} />
      {confirmationDialog}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-600 hover:text-gray-600"
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
            className="ml-4 text-status-error-800 hover:text-status-error-800"
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
                      ? 'border-ui-gold-500 text-ui-gold-800'
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
                  <p className="break-words text-sm font-medium text-gray-900 bg-gray-50 p-3 rounded">
                    {submission.Original_Headline}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Original Body
                  </label>
                  <p className="break-words text-sm text-gray-700 bg-gray-50 p-3 rounded whitespace-pre-wrap">
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
                  onChange={handleViewModeChange}
                  options={[
                    { value: 'side_by_side', label: 'Side by Side' },
                    { value: 'diff', label: 'Inline Diff' },
                    { value: 'live', label: 'Live View' },
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

                {viewMode === 'live' && (
                  <section aria-label="AI live edit" className="min-w-0 space-y-4">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">Live View</h3>
                      <p className="mt-1 text-xs text-gray-500">
                        Edit the AI suggestion, then save a draft or approve it from this view.
                      </p>
                    </div>
                    {editingFields}
                    {conflictPanel}
                    {finalizationControls}
                  </section>
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
                  className="min-w-0 space-y-4 rounded-lg border border-gray-200 bg-gray-50 p-4 lg:sticky lg:top-6 lg:self-start"
                >
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">Original submission</h3>
                    <p className="mt-1 text-xs text-gray-500">Read-only reference</p>
                  </div>
                  <OriginalSubmissionFields submission={submission} />
                </section>

                <section aria-label="Final edit" className="min-w-0 space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">Final edit</h3>
                    <p className="mt-1 text-xs text-gray-500">
                      Starting point: {finalEditSourceLabel}
                    </p>
                  </div>
                  {editingFields}
                  {conflictPanel}
                  {finalizationControls}
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
            onUpdateScheduleEnding={isStaff ? handleUpdateScheduleEnding : undefined}
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
                <label className="block text-xs font-medium text-gray-500 mb-1" htmlFor="control-editpage-1">
                  Assigned Editor
                </label>
                <input
                  type="text"
                  value={assignedEditor}
                  onChange={(e) => setAssignedEditor(e.target.value)}
                  placeholder="e.g., Jane Smith"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                  id="control-editpage-1"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1" htmlFor="control-editpage-2">
                  Internal Notes
                </label>
                <textarea
                  value={editorialNotes}
                  onChange={(e) => setEditorialNotes(e.target.value)}
                  rows={5}
                  placeholder="Internal handoff notes, follow-up items, source context, or pending questions."
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                  id="control-editpage-2"
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
                  className="flex-1 bg-status-attention-800 text-white hover:bg-status-attention-800"
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
