import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import {
  addAcademicDate,
  addJobPosting,
  addCalendarEvent,
  listNewsletters,
  listCalendarEvents,
  listJobPostings,
  getNewsletter,
  assembleNewsletter,
  updateNewsletterStatus,
  removeNewsletterExternalItem,
  removeNewsletterItem,
  reorderNewsletterItems,
  getExportUrl,
  listSections,
  updateNewsletterItem,
} from '../api/newsletters';
import {
  addRecurringMessageToNewsletter,
  listRecurringMessageCandidates,
  skipRecurringMessageForNewsletter,
} from '../api/recurringMessages';
import type {
  CalendarEventCandidate,
  JobPostingCandidate,
  NewsletterDetailResponse,
} from '../api/newsletters';
import type { NewsletterSection } from '../types/newsletter';
import type { RecurringMessageIssueCandidate } from '../types/recurringMessage';
import { EmptyState, Toast, useToast } from '../components/common';
import RichBody from '../components/editor/RichBody';
import {
  buildLinkedBody,
  prepareBodyForEditing,
  type EditableBodyLink,
} from '../utils/bodyLinks';
import { parseISODate, todayISO, toISODate } from '../utils/date';

const ACADEMIC_DATES_SOURCE_URL = 'https://www.uidaho.edu/registrar/dates-deadlines';
const ACADEMIC_DATES_WINDOW_DAYS = 30;

interface BuilderSectionItemBase {
  Id: string;
  Section_Id: string;
  Position: number;
  Final_Headline: string;
  Final_Body: string;
}

interface SubmissionDragState {
  itemId: string;
  sourceSectionId: string;
  overSectionId: string | null;
  overIndex: number | null;
  pointerX: number;
  pointerY: number;
  offsetX: number;
  offsetY: number;
  width: number;
  height: number;
  title: string;
}

interface NewsletterItemEditDraft {
  Item_Id: string;
  Headline: string;
  Body: string;
  Links: EditableBodyLink[];
}

type BuilderSectionItem =
  | (BuilderSectionItemBase & { Kind: 'submission'; Run_Number: number })
  | (BuilderSectionItemBase & {
    Kind: 'calendar_event';
    Source_Id: string;
    Source_Url: string | null;
    Location: string | null;
    Event_Start: string | null;
    Source_Type: string;
  })
  | (BuilderSectionItemBase & {
    Kind: 'job_posting';
    Source_Id: string;
    Source_Url: string | null;
    Location: string | null;
    Posting_Number?: string | null;
    Source_Type: string;
  })
  | (BuilderSectionItemBase & {
    Kind: 'recurring_message';
    Source_Id: string;
    Source_Type: string;
  })
  | (BuilderSectionItemBase & {
    Kind: 'academic_date';
    Source_Id: string;
    Source_Url: string | null;
    Event_Start: string | null;
    Source_Type: string;
  });

interface CollapsibleCardProps {
  title: string;
  subtitle?: string;
  meta?: string;
  isOpen: boolean;
  onToggle: () => void;
  actions?: ReactNode;
  children: ReactNode;
}

type ImportPanelKey = 'recurringMessages' | 'calendarEvents' | 'jobPostings';

function CollapsibleCard({
  title,
  subtitle,
  meta,
  isOpen,
  onToggle,
  actions,
  children,
}: CollapsibleCardProps) {
  return (
    <div className="bg-white rounded-lg shadow">
      <div className="flex items-center justify-between gap-4 px-4 py-3 border-b border-gray-100">
        <button
          type="button"
          onClick={onToggle}
          className="min-w-0 flex-1 text-left"
          aria-expanded={isOpen}
        >
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">{isOpen ? '▾' : '▸'}</span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
                {meta && <span className="text-xs text-gray-400">{meta}</span>}
              </div>
              {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
            </div>
          </div>
        </button>
        {actions && <div className="shrink-0">{actions}</div>}
      </div>
      {isOpen && <div className="p-4">{children}</div>}
    </div>
  );
}

interface ImportCandidatePillProps {
  label: string;
  count: number;
  loading: boolean;
  isOpen: boolean;
  onClick: () => void;
}

function ImportCandidatePill({
  label,
  count,
  loading,
  isOpen,
  onClick,
}: ImportCandidatePillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
        isOpen
          ? 'border-ui-clearwater-300 bg-ui-clearwater-50 text-ui-clearwater-800'
          : 'border-gray-200 bg-white text-gray-700 hover:border-ui-clearwater-300 hover:text-ui-clearwater-800'
      }`}
      aria-pressed={isOpen}
    >
      + {loading ? '...' : count} {label}
    </button>
  );
}

export default function BuilderPage() {
  const [newsletterType, setNewsletterType] = useState<'tdr' | 'myui'>('tdr');
  const [publishDate, setPublishDate] = useState(todayISO());
  const [newsletter, setNewsletter] = useState<NewsletterDetailResponse | null>(null);
  const [newsletters, setNewsletters] = useState<NewsletterDetailResponse[]>([]);
  const [sections, setSections] = useState<NewsletterSection[]>([]);
  const [recurringMessages, setRecurringMessages] = useState<RecurringMessageIssueCandidate[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEventCandidate[]>([]);
  const [jobPostings, setJobPostings] = useState<JobPostingCandidate[]>([]);
  const [recurringLoading, setRecurringLoading] = useState(false);
  const [recurringError, setRecurringError] = useState<string | null>(null);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarError, setCalendarError] = useState<string | null>(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const [academicDate, setAcademicDate] = useState('');
  const [academicTitle, setAcademicTitle] = useState('');
  const [academicDescription, setAcademicDescription] = useState('');
  const [academicSaving, setAcademicSaving] = useState(false);
  const [panelOpen, setPanelOpen] = useState({
    recurringMessages: false,
    calendarEvents: false,
    jobPostings: false,
  });
  const [sectionOpen, setSectionOpen] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast, showToast, dismissToast } = useToast();
  const [dragState, setDragState] = useState<SubmissionDragState | null>(null);
  const [itemEditDraft, setItemEditDraft] = useState<NewsletterItemEditDraft | null>(null);
  const [itemEditSaving, setItemEditSaving] = useState(false);
  const dragStateRef = useRef<SubmissionDragState | null>(null);
  const newsletterId = newsletter?.Id;

  useEffect(() => {
    void (async () => {
      try {
        const [secs, list] = await Promise.all([
          listSections(newsletterType),
          listNewsletters({ newsletter_type: newsletterType }),
        ]);
        setSections(secs);
        setNewsletters(list as NewsletterDetailResponse[]);
      } catch (err) {
        console.error('Failed to load builder metadata:', err);
      }
    })();
  }, [newsletterType]);

  useEffect(() => {
    if (!newsletterId) {
      setRecurringMessages([]);
      setRecurringError(null);
      setCalendarEvents([]);
      setCalendarError(null);
      setJobPostings([]);
      setJobError(null);
      return;
    }
    void loadRecurringMessages(newsletterId);
    void loadCalendarEvents(newsletterId);
    void loadJobPostings(newsletterId);
  }, [newsletterId]);

  useEffect(() => {
    dragStateRef.current = dragState;
  }, [dragState]);

  const loadNewsletters = async () => {
    try {
      const list = await listNewsletters({ newsletter_type: newsletterType });
      setNewsletters(list as NewsletterDetailResponse[]);
    } catch (err) {
      console.error('Failed to load newsletters:', err);
    }
  };

  const loadRecurringMessages = async (newsletterId: string) => {
    setRecurringLoading(true);
    setRecurringError(null);
    try {
      const messages = await listRecurringMessageCandidates(newsletterId);
      setRecurringMessages(messages);
    } catch (err) {
      setRecurringError(err instanceof Error ? err.message : 'Failed to load recurring messages');
    } finally {
      setRecurringLoading(false);
    }
  };

  const loadCalendarEvents = async (newsletterId: string) => {
    setCalendarLoading(true);
    setCalendarError(null);
    try {
      const events = await listCalendarEvents(newsletterId);
      setCalendarEvents(events);
    } catch (err) {
      setCalendarError(err instanceof Error ? err.message : 'Failed to load calendar events');
    } finally {
      setCalendarLoading(false);
    }
  };

  const loadJobPostings = async (newsletterId: string) => {
    setJobLoading(true);
    setJobError(null);
    try {
      const postings = await listJobPostings(newsletterId);
      setJobPostings(postings);
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'Failed to load job postings');
    } finally {
      setJobLoading(false);
    }
  };

  const handleAddRecurringMessage = async (recurringMessageId: string) => {
    if (!newsletter) return;
    try {
      await addRecurringMessageToNewsletter(newsletter.Id, recurringMessageId);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      await loadRecurringMessages(newsletter.Id);
      showToast('Recurring message added');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add recurring message');
    }
  };

  const handleSkipRecurringMessage = async (recurringMessageId: string) => {
    if (!newsletter) return;
    try {
      await skipRecurringMessageForNewsletter(newsletter.Id, recurringMessageId);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      await loadRecurringMessages(newsletter.Id);
      showToast('Recurring message skipped for this issue');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip recurring message');
    }
  };

  const handleAssemble = async () => {
    setLoading(true);
    setError(null);
    try {
      const nl = await assembleNewsletter({
        Newsletter_Type: newsletterType,
        Publish_Date: publishDate,
      });
      setNewsletter(nl);
      showToast(`Newsletter assembled with ${nl.Items.length} items`);
      loadNewsletters();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Assembly failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadNewsletter = async (id: string) => {
    setLoading(true);
    try {
      const nl = await getNewsletter(id);
      setNewsletter(nl);
      setPublishDate(nl.Publish_Date);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveItem = async (itemId: string) => {
    if (!newsletter) return;
    try {
      await removeNewsletterItem(newsletter.Id, itemId);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      showToast('Item removed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove');
    }
  };

  const handleRemoveExternalItem = async (
    itemId: string,
    sourceType?: string,
    sourceId?: string,
  ) => {
    if (!newsletter) return;
    try {
      if (sourceType === 'recurring_message' && sourceId) {
        await skipRecurringMessageForNewsletter(newsletter.Id, sourceId);
      } else {
        await removeNewsletterExternalItem(newsletter.Id, itemId);
      }
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      await loadRecurringMessages(newsletter.Id);
      await loadCalendarEvents(newsletter.Id);
      await loadJobPostings(newsletter.Id);
      showToast('Imported item removed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove imported item');
    }
  };

  const handleAddCalendarEvent = async (event: CalendarEventCandidate) => {
    if (!newsletter) return;
    try {
      await addCalendarEvent(newsletter.Id, {
        Source_Id: event.Source_Id,
        Url: event.Url,
        Title: event.Title,
        Description: event.Description,
        Location: event.Location,
        Event_Start: event.Event_Start,
        Event_End: event.Event_End,
      });
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      await loadCalendarEvents(newsletter.Id);
      showToast('Calendar event added');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add calendar event');
    }
  };

  const handleAddJobPosting = async (posting: JobPostingCandidate) => {
    if (!newsletter) return;
    try {
      await addJobPosting(newsletter.Id, {
        Source_Id: posting.Source_Id,
        Url: posting.Url,
        Title: posting.Title,
        Department: posting.Department,
        Posting_Number: posting.Posting_Number,
        Location: posting.Location,
        Closing_Date: posting.Closing_Date,
        Summary: posting.Summary,
      });
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      await loadJobPostings(newsletter.Id);
      showToast('Job posting added');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add job posting');
    }
  };

  const handleAddAcademicDate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newsletter || !academicDate || !academicTitle.trim()) return;

    setAcademicSaving(true);
    setError(null);
    try {
      await addAcademicDate(newsletter.Id, {
        Academic_Date: academicDate,
        Title: academicTitle.trim(),
        Description: academicDescription.trim() || null,
      });
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      setAcademicDate('');
      setAcademicTitle('');
      setAcademicDescription('');
      showToast('Academic date added');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add academic date');
    } finally {
      setAcademicSaving(false);
    }
  };

  const handleMoveItem = async (itemId: string, direction: 'up' | 'down') => {
    if (!newsletter) return;

    const item = newsletter.Items.find((i) => i.Id === itemId);
    if (!item) return;

    // Get items in same section, sorted by position
    const sectionItems = newsletter.Items
      .filter((i) => i.Section_Id === item.Section_Id)
      .sort((a, b) => a.Position - b.Position);

    const idx = sectionItems.findIndex((i) => i.Id === itemId);
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= sectionItems.length) return;

    const positions = sectionItems.map((i, index) => {
      if (index === idx) return { Id: i.Id, Position: swapIdx };
      if (index === swapIdx) return { Id: i.Id, Position: idx };
      return { Id: i.Id, Position: index };
    });

    try {
      await reorderNewsletterItems(newsletter.Id, positions);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reorder');
    }
  };

  const buildSubmissionReorderPositions = useCallback((
    itemId: string,
    targetSectionId: string,
    targetIndex: number,
  ) => {
    if (!newsletter) return [];

    const draggedItem = newsletter.Items.find((item) => item.Id === itemId);
    if (!draggedItem) return [];

    const sourceSectionId = draggedItem.Section_Id;
    const sourceItems = newsletter.Items
      .filter((item) => item.Section_Id === sourceSectionId && item.Id !== itemId)
      .sort((a, b) => a.Position - b.Position);
    const targetItemsBase = newsletter.Items
      .filter((item) => item.Section_Id === targetSectionId && item.Id !== itemId)
      .sort((a, b) => a.Position - b.Position);

    if (sourceSectionId === targetSectionId) {
      const clampedIndex = Math.max(0, Math.min(targetIndex, sourceItems.length));
      const reorderedItems = [...sourceItems];
      reorderedItems.splice(clampedIndex, 0, draggedItem);
      return reorderedItems.map((item, index) => ({
        Id: item.Id,
        Position: index,
        Section_Id: targetSectionId,
      }));
    }

    const clampedIndex = Math.max(0, Math.min(targetIndex, targetItemsBase.length));
    const targetItems = [...targetItemsBase];
    targetItems.splice(clampedIndex, 0, draggedItem);

    return [
      ...sourceItems.map((item, index) => ({
        Id: item.Id,
        Position: index,
        Section_Id: sourceSectionId,
      })),
      ...targetItems.map((item, index) => ({
        Id: item.Id,
        Position: index,
        Section_Id: targetSectionId,
      })),
    ];
  }, [newsletter]);

  const handleReassignSubmission = useCallback(async (
    itemId: string,
    targetSectionId: string,
    targetIndex?: number,
  ) => {
    if (!newsletter) return;

    const draggedItem = newsletter.Items.find((item) => item.Id === itemId);
    if (!draggedItem) return;

    const targetItems = newsletter.Items.filter(
      (item) => item.Section_Id === targetSectionId && item.Id !== itemId,
    );
    const positions = buildSubmissionReorderPositions(
      itemId,
      targetSectionId,
      targetIndex ?? targetItems.length,
    );
    if (positions.length === 0) return;

    try {
      await reorderNewsletterItems(newsletter.Id, positions);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reorder');
    }
  }, [buildSubmissionReorderPositions, newsletter]);

  const handleStatusChange = async (status: string) => {
    if (!newsletter) return;
    try {
      await updateNewsletterStatus(newsletter.Id, status);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      showToast(`Status updated to ${status.replace('_', ' ')}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const beginNewsletterItemEdit = (
    item: Extract<BuilderSectionItem, { Kind: 'submission' }>,
  ) => {
    const editable = prepareBodyForEditing(item.Final_Body);
    setItemEditDraft({
      Item_Id: item.Id,
      Headline: item.Final_Headline,
      Body: editable.body,
      Links: editable.links,
    });
  };

  const handleSaveNewsletterItem = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newsletter || !itemEditDraft) return;

    const headline = itemEditDraft.Headline.trim();
    const body = itemEditDraft.Body.trim();
    if (!headline || !body) {
      setError('Newsletter headline and body are required');
      return;
    }

    setItemEditSaving(true);
    setError(null);
    try {
      await updateNewsletterItem(newsletter.Id, itemEditDraft.Item_Id, {
        Final_Headline: headline,
        Final_Body: buildLinkedBody(body, itemEditDraft.Links),
      });
      const refreshed = await getNewsletter(newsletter.Id);
      setNewsletter(refreshed);
      setItemEditDraft(null);
      showToast('Newsletter text updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update newsletter text');
    } finally {
      setItemEditSaving(false);
    }
  };

  const togglePanel = (panel: ImportPanelKey) => {
    setPanelOpen((current) => ({
      ...current,
      [panel]: !current[panel],
    }));
  };

  const toggleSection = (sectionId: string) => {
    setSectionOpen((current) => ({
      ...current,
      [sectionId]: !(current[sectionId] ?? true),
    }));
  };

  const getDropTargetFromPoint = (clientX: number, clientY: number) => {
    const hovered = document.elementFromPoint(clientX, clientY);
    const hoveredCard = hovered?.closest('[data-draggable-card="true"]') as HTMLElement | null;
    const hoveredSection = hovered?.closest('[data-builder-section-id]') as HTMLElement | null;

    if (hoveredCard && hoveredCard.dataset.itemKind === 'submission') {
      const sectionId = hoveredCard.dataset.sectionId;
      const itemId = hoveredCard.dataset.itemId;
      const index = Number(hoveredCard.dataset.submissionIndex ?? '-1');
      if (sectionId && itemId && itemId !== dragStateRef.current?.itemId && index >= 0) {
        const rect = hoveredCard.getBoundingClientRect();
        return {
          sectionId,
          index: clientY > rect.top + rect.height / 2 ? index + 1 : index,
        };
      }
    }

    if (hoveredSection?.dataset.builderSectionId) {
      const sectionId = hoveredSection.dataset.builderSectionId;
      const submissionCount = Number(hoveredSection.dataset.submissionCount ?? '0');
      return { sectionId, index: submissionCount };
    }

    return { sectionId: null, index: null };
  };

  const startSubmissionDrag = (
    item: Extract<BuilderSectionItem, { Kind: 'submission' }>,
    event: React.PointerEvent<HTMLButtonElement>,
  ) => {
    if (!newsletter) return;

    event.preventDefault();
    event.stopPropagation();

    const card = event.currentTarget.closest('[data-draggable-card="true"]') as HTMLElement | null;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const initialDropTarget = getDropTargetFromPoint(event.clientX, event.clientY);
    setDragState({
      itemId: item.Id,
      sourceSectionId: item.Section_Id,
      overSectionId: initialDropTarget.sectionId ?? item.Section_Id,
      overIndex: initialDropTarget.index ?? 0,
      pointerX: event.clientX,
      pointerY: event.clientY,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
      width: rect.width,
      height: rect.height,
      title: item.Final_Headline,
    });
  };

  useEffect(() => {
    if (!dragState || !newsletter) return;

    const handlePointerMove = (event: PointerEvent) => {
      event.preventDefault();
      const dropTarget = getDropTargetFromPoint(event.clientX, event.clientY);
      setDragState((current) => current ? {
        ...current,
        pointerX: event.clientX,
        pointerY: event.clientY,
        overSectionId: dropTarget.sectionId,
        overIndex: dropTarget.index,
      } : current);
    };

    const handlePointerUp = async () => {
      const currentDrag = dragStateRef.current;
      setDragState(null);
      if (!currentDrag?.overSectionId || currentDrag.overIndex === null) return;
      await handleReassignSubmission(
        currentDrag.itemId,
        currentDrag.overSectionId,
        currentDrag.overIndex,
      );
    };

    const originalUserSelect = document.body.style.userSelect;
    const originalCursor = document.body.style.cursor;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'grabbing';
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp, { once: true });

    return () => {
      document.body.style.userSelect = originalUserSelect;
      document.body.style.cursor = originalCursor;
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [dragState, handleReassignSubmission, newsletter]);

  // Group items by section
  const itemsBySection = new Map<string, BuilderSectionItem[]>();
  const submissionItemsBySection = new Map<string, BuilderSectionItem[]>();
  if (newsletter) {
    const submissionItems: BuilderSectionItem[] = newsletter.Items.map((item) => ({
      ...item,
      Kind: 'submission',
    }));
    const externalItems: BuilderSectionItem[] = newsletter.External_Items.map((item) => ({
      Id: item.Id,
      Source_Id: item.Source_Id,
      Section_Id: item.Section_Id,
      Position: item.Position,
      Final_Headline: item.Final_Headline,
      Final_Body: item.Final_Body,
      Kind: item.Source_Type === 'job_posting'
        ? 'job_posting'
        : item.Source_Type === 'recurring_message'
          ? 'recurring_message'
          : item.Source_Type === 'academic_date'
            ? 'academic_date'
            : 'calendar_event',
      Source_Url: item.Source_Url,
      Location: item.Location,
      Event_Start: item.Event_Start,
      Source_Type: item.Source_Type,
    }));
    const allItems = [...submissionItems, ...externalItems];
    for (const section of sections) {
      const items = allItems
        .filter((i) => i.Section_Id === section.Id)
        .sort((a, b) => a.Position - b.Position || a.Final_Headline.localeCompare(b.Final_Headline));
      if (items.length > 0) {
        itemsBySection.set(section.Id, items);
      }
      submissionItemsBySection.set(
        section.Id,
        items.filter((item) => item.Kind === 'submission'),
      );
    }
  }

  const isDropIndicatorVisible = (sectionId: string, index: number) => (
    dragState?.overSectionId === sectionId && dragState.overIndex === index
  );

  const sectionNameById = new Map(sections.map((section) => [section.Id, section.Name]));
  const academicDateMax = newsletter
    ? (() => {
        const maxDate = parseISODate(newsletter.Publish_Date);
        maxDate.setDate(maxDate.getDate() + ACADEMIC_DATES_WINDOW_DAYS);
        return toISODate(maxDate);
      })()
    : '';

  const STATUS_COLORS: Record<string, string> = {
    draft: 'bg-status-muted-100 text-status-muted-800',
    in_progress: 'bg-status-info-100 text-status-info-800',
    ready_for_review: 'bg-status-warning-100 text-status-warning-800',
    submitted: 'bg-ui-clearwater-100 text-ui-clearwater-800',
    published: 'bg-status-success-100 text-status-success-800',
  };

  return (
    <div>
      {/* Toast */}
      <Toast toast={toast} onDismiss={dismissToast} />
      {dragState && (
        <div
          className="pointer-events-none fixed z-50 rounded-lg border border-ui-gold-300 bg-white/95 px-4 py-3 shadow-2xl ring-2 ring-ui-gold-200"
          style={{
            left: dragState.pointerX - dragState.offsetX,
            top: dragState.pointerY - dragState.offsetY,
            width: dragState.width,
            minHeight: dragState.height,
          }}
        >
          <div className="flex items-center gap-2 text-xs text-ui-gold-700 mb-1">
            <span className="tracking-wide uppercase">Dragging</span>
          </div>
          <p className="text-sm font-medium text-gray-900 line-clamp-2">{dragState.title}</p>
        </div>
      )}

      <h2 className="text-2xl font-bold text-gray-900 mb-6">Newsletter Builder</h2>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label htmlFor="builder-newsletter-type" className="block text-xs text-gray-500 mb-1">
              Newsletter
            </label>
            <select
              id="builder-newsletter-type"
              value={newsletterType}
              onChange={(e) => {
                setNewsletterType(e.target.value as 'tdr' | 'myui');
                setNewsletter(null);
              }}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="tdr">The Daily Register</option>
              <option value="myui">My UI</option>
            </select>
          </div>
          <div>
            <label htmlFor="builder-publish-date" className="block text-xs text-gray-500 mb-1">
              Publish Date
            </label>
            <input
              id="builder-publish-date"
              type="date"
              value={publishDate}
              onChange={(e) => setPublishDate(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleAssemble}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium rounded-md bg-ui-gold-600 text-white hover:bg-ui-gold-700 disabled:opacity-50"
          >
            {loading ? 'Assembling...' : 'Assemble Newsletter'}
          </button>
          {newsletter && (
            <>
              <a
                href={getExportUrl(newsletter.Id)}
                className="px-4 py-2 text-sm font-medium rounded-md bg-ui-clearwater-600 text-white hover:bg-ui-clearwater-700"
                download
              >
                Export Word Doc
              </a>
              <select
                value={newsletter.Status}
                onChange={(e) => handleStatusChange(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="draft">Draft</option>
                <option value="in_progress">In Progress</option>
                <option value="ready_for_review">Ready for Review</option>
                <option value="submitted">Submitted</option>
                <option value="published">Published</option>
              </select>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main builder area */}
        <div className="lg:col-span-3">
          {!newsletter ? (
            <EmptyState
              title="No newsletter loaded"
              description="Choose a newsletter type and publish date, then assemble the issue from approved submissions."
              actionLabel={loading ? undefined : 'Assemble Newsletter'}
              onAction={loading ? undefined : () => void handleAssemble()}
            />
          ) : (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <ImportCandidatePill
                  label="recurring"
                  count={recurringMessages.length}
                  loading={recurringLoading}
                  isOpen={panelOpen.recurringMessages}
                  onClick={() => togglePanel('recurringMessages')}
                />
                <ImportCandidatePill
                  label="events"
                  count={calendarEvents.length}
                  loading={calendarLoading}
                  isOpen={panelOpen.calendarEvents}
                  onClick={() => togglePanel('calendarEvents')}
                />
                <ImportCandidatePill
                  label="jobs"
                  count={jobPostings.length}
                  loading={jobLoading}
                  isOpen={panelOpen.jobPostings}
                  onClick={() => togglePanel('jobPostings')}
                />
              </div>

              {panelOpen.recurringMessages && (
                <CollapsibleCard
                  title="Recurring Messages"
                  subtitle="Reusable editorial copy surfaced from the recurring-message library."
                  meta={`${recurringMessages.length} candidate${recurringMessages.length !== 1 ? 's' : ''}`}
                  isOpen
                  onToggle={() => togglePanel('recurringMessages')}
                  actions={(
                    <button
                      onClick={() => void loadRecurringMessages(newsletter.Id)}
                      disabled={recurringLoading}
                      className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {recurringLoading ? 'Refreshing...' : 'Refresh Messages'}
                    </button>
                  )}
                >
                  {recurringError && (
                    <div className="mb-3 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                      {recurringError}
                    </div>
                  )}
                  {recurringMessages.length === 0 ? (
                    <EmptyState
                      title={recurringLoading ? 'Loading recurring messages' : 'No recurring messages apply'}
                      description="Reusable messages appear here when their cadence matches this newsletter issue date."
                      framed={false}
                    />
                  ) : (
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                      {recurringMessages.map((message) => (
                        <div
                          key={message.Id}
                          className={`rounded-lg border p-3 ${
                            message.Selected
                              ? 'border-green-200 bg-green-50'
                              : message.Skipped
                                ? 'border-amber-200 bg-amber-50'
                                : 'border-gray-200 bg-white'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <p className="text-sm font-medium text-gray-900">{message.Headline}</p>
                                {message.Selected && (
                                  <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-medium text-green-700">
                                    Added
                                  </span>
                                )}
                                {message.Skipped && (
                                  <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                                    Skipped
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 mt-1">
                                {sectionNameById.get(message.Section_Id) ?? 'Unknown section'}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => void handleAddRecurringMessage(message.Id)}
                                disabled={message.Selected}
                                className={`px-3 py-1.5 text-xs font-medium rounded-md ${
                                  message.Selected
                                    ? 'bg-green-100 text-green-700 cursor-default'
                                    : 'bg-ui-gold-600 text-white hover:bg-ui-gold-700'
                                }`}
                              >
                                {message.Skipped ? 'Restore' : message.Selected ? 'Added' : 'Add'}
                              </button>
                              <button
                                onClick={() => void handleSkipRecurringMessage(message.Id)}
                                disabled={message.Skipped}
                                className={`px-3 py-1.5 text-xs font-medium rounded-md border ${
                                  message.Skipped
                                    ? 'border-amber-200 text-amber-700 bg-amber-100 cursor-default'
                                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                                }`}
                              >
                                Skip
                              </button>
                            </div>
                          </div>
                          <p className="text-xs text-gray-600 mt-2 line-clamp-3">
                            {message.Body}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </CollapsibleCard>
              )}

              {panelOpen.calendarEvents && (
              <CollapsibleCard
                title="Import Calendar Events"
                subtitle={`Pull upcoming events from the U of I events calendar into the ${
                  newsletterType === 'tdr' ? "Today's Events" : 'Weekly Events'
                } section. These are external calendar events, not submitted announcements.`}
                meta={`${calendarEvents.length} candidate${calendarEvents.length !== 1 ? 's' : ''}`}
                isOpen
                onToggle={() => togglePanel('calendarEvents')}
                actions={(
                  <button
                    onClick={() => loadCalendarEvents(newsletter.Id)}
                    disabled={calendarLoading}
                    className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {calendarLoading ? 'Refreshing...' : 'Refresh Events'}
                  </button>
                )}
              >
                {calendarError && (
                  <div className="mb-3 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                    {calendarError}
                  </div>
                )}
                {calendarEvents.length === 0 ? (
                  <EmptyState
                    title={calendarLoading ? 'Loading candidate events' : 'No candidate events found'}
                    description="External calendar events appear here when they fall inside this issue window."
                    framed={false}
                  />
                ) : (
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                    {calendarEvents.map((event) => (
                      <div
                        key={event.Source_Id}
                        className={`rounded-lg border p-3 ${
                          event.Selected ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900">{event.Title}</p>
                            <p className="text-xs text-gray-500 mt-1">
                              {event.Event_Start
                                ? new Date(event.Event_Start).toLocaleString('en-US', {
                                  weekday: 'short',
                                  month: 'short',
                                  day: 'numeric',
                                  hour: 'numeric',
                                  minute: '2-digit',
                                })
                                : 'Date unavailable'}
                            </p>
                            {event.Location && (
                              <p className="text-xs text-gray-500 mt-1">{event.Location}</p>
                            )}
                          </div>
                          <button
                            onClick={() => handleAddCalendarEvent(event)}
                            disabled={event.Selected}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md ${
                              event.Selected
                                ? 'bg-green-100 text-green-700 cursor-default'
                                : 'bg-ui-clearwater-600 text-white hover:bg-ui-clearwater-700'
                            }`}
                          >
                            {event.Selected ? 'Added' : 'Add'}
                          </button>
                        </div>
                        <p className="text-xs text-gray-600 mt-2 line-clamp-3">
                          {event.Description}
                        </p>
                        {event.Url && (
                          <a
                            href={event.Url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-block mt-2 text-xs text-ui-clearwater-700 hover:text-ui-clearwater-800"
                          >
                            View source
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CollapsibleCard>
              )}

              {panelOpen.jobPostings && (
              <CollapsibleCard
                title="Job Postings"
                subtitle={`Import U of I job postings into the ${
                  newsletterType === 'tdr' ? 'Job Opportunities' : 'Help Wanted'
                } section.`}
                meta={`${jobPostings.length} candidate${jobPostings.length !== 1 ? 's' : ''}`}
                isOpen
                onToggle={() => togglePanel('jobPostings')}
                actions={(
                  <button
                    onClick={() => loadJobPostings(newsletter.Id)}
                    disabled={jobLoading}
                    className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {jobLoading ? 'Refreshing...' : 'Refresh Jobs'}
                  </button>
                )}
              >
                {jobError && (
                  <div className="mb-3 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                    {jobError}
                  </div>
                )}
                {jobPostings.length === 0 ? (
                  <EmptyState
                    title={jobLoading ? 'Loading job postings' : 'No candidate job postings found'}
                    description="Open postings appear here when they are available from the U of I jobs source."
                    framed={false}
                  />
                ) : (
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                    {jobPostings.map((posting) => (
                      <div
                        key={posting.Source_Id}
                        className={`rounded-lg border p-3 ${
                          posting.Selected ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-gray-900">{posting.Title}</p>
                            <p className="text-xs text-gray-500 mt-1">
                              {[
                                posting.Department,
                                posting.Location,
                                posting.Posting_Number,
                              ].filter(Boolean).join(' • ') || 'University of Idaho jobs portal'}
                            </p>
                            {posting.Closing_Date && (
                              <p className="text-xs text-gray-500 mt-1">
                                Closes {posting.Closing_Date}
                              </p>
                            )}
                          </div>
                          <button
                            onClick={() => handleAddJobPosting(posting)}
                            disabled={posting.Selected}
                            className={`px-3 py-1.5 text-xs font-medium rounded-md ${
                              posting.Selected
                                ? 'bg-green-100 text-green-700 cursor-default'
                                : 'bg-ui-gold-600 text-white hover:bg-ui-gold-700'
                            }`}
                          >
                            {posting.Selected ? 'Added' : 'Add'}
                          </button>
                        </div>
                        <p className="text-xs text-gray-600 mt-2 line-clamp-3">
                          {posting.Summary}
                        </p>
                        <a
                          href={posting.Url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-block mt-2 text-xs text-ui-clearwater-700 hover:text-ui-clearwater-800"
                        >
                          View source
                        </a>
                      </div>
                    ))}
                  </div>
                )}
              </CollapsibleCard>
              )}

              {/* Newsletter header */}
              <div className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">
                    {newsletterType === 'tdr' ? 'The Daily Register' : 'My UI'}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {parseISODate(newsletter.Publish_Date).toLocaleDateString('en-US', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLORS[newsletter.Status] || 'bg-gray-100'}`}
                  >
                    {newsletter.Status.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-gray-400">
                    {newsletter.Items.length + newsletter.External_Items.length} item
                    {newsletter.Items.length + newsletter.External_Items.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>

              {/* Sections with items */}
              {sections.map((section) => {
                const items = itemsBySection.get(section.Id) || [];
                const submissionItems = submissionItemsBySection.get(section.Id) || [];
                const isOpen = sectionOpen[section.Id] ?? true;
                const isDropSection = dragState?.overSectionId === section.Id;
                const isAcademicDatesSection = newsletterType === 'myui'
                  && section.Slug === 'academic-dates-and-deadlines';
                return (
                  <div key={section.Id} className="bg-white rounded-lg shadow">
                    <button
                      type="button"
                      onClick={() => toggleSection(section.Id)}
                      className="w-full px-4 py-3 border-b border-gray-100 flex items-center justify-between gap-4 text-left"
                      aria-expanded={isOpen}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="text-sm text-gray-400">{isOpen ? '▾' : '▸'}</span>
                        <h4 className="text-sm font-semibold text-gray-900">
                          {section.Name}
                        </h4>
                      </div>
                      <span className="text-xs text-gray-400">
                        {items.length} item{items.length !== 1 ? 's' : ''}
                      </span>
                    </button>
                    {isOpen && (
                      <div
                        data-builder-section-id={section.Id}
                        data-submission-count={submissionItems.length}
                        className={`transition-colors ${
                          isDropSection ? 'bg-ui-gold-50/70 ring-2 ring-inset ring-ui-gold-300' : ''
                        }`}
                      >
                        {isAcademicDatesSection && (
                          <div className="border-b border-gray-100 bg-ui-clearwater-50/50 p-4">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <h5 className="text-sm font-semibold text-gray-900">
                                  Add from the Registrar calendar
                                </h5>
                                <p className="mt-1 max-w-2xl text-xs text-gray-600">
                                  Copy the date and wording from the official calendar. My UI includes
                                  deadlines from the publication date through the next 30 days.
                                </p>
                              </div>
                              <a
                                href={ACADEMIC_DATES_SOURCE_URL}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs font-medium text-ui-clearwater-700 hover:text-ui-clearwater-900"
                              >
                                Open Registrar calendar ↗
                              </a>
                            </div>
                            <form
                              className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-6"
                              onSubmit={handleAddAcademicDate}
                            >
                              <div className="md:col-span-2">
                                <label
                                  htmlFor="academic-deadline-date"
                                  className="block text-xs font-medium text-gray-700"
                                >
                                  Deadline date
                                </label>
                                <input
                                  id="academic-deadline-date"
                                  type="date"
                                  min={newsletter.Publish_Date}
                                  max={academicDateMax}
                                  value={academicDate}
                                  onChange={(event) => setAcademicDate(event.target.value)}
                                  required
                                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                                />
                              </div>
                              <div className="md:col-span-4">
                                <label
                                  htmlFor="academic-deadline-title"
                                  className="block text-xs font-medium text-gray-700"
                                >
                                  Academic date or deadline
                                </label>
                                <input
                                  id="academic-deadline-title"
                                  type="text"
                                  value={academicTitle}
                                  onChange={(event) => setAcademicTitle(event.target.value)}
                                  placeholder="Paste the deadline wording"
                                  required
                                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                                />
                              </div>
                              <div className="md:col-span-4">
                                <label
                                  htmlFor="academic-deadline-details"
                                  className="block text-xs font-medium text-gray-700"
                                >
                                  Details (optional)
                                </label>
                                <textarea
                                  id="academic-deadline-details"
                                  rows={2}
                                  value={academicDescription}
                                  onChange={(event) => setAcademicDescription(event.target.value)}
                                  placeholder="Paste any audience or term details that should appear in My UI"
                                  className="mt-1 w-full resize-y rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                                />
                              </div>
                              <div className="flex items-end md:col-span-2">
                                <button
                                  type="submit"
                                  disabled={academicSaving || !academicDate || !academicTitle.trim()}
                                  className="w-full rounded-md bg-ui-gold-600 px-3 py-2 text-sm font-medium text-white hover:bg-ui-gold-700 disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                  {academicSaving ? 'Adding...' : 'Add academic date'}
                                </button>
                              </div>
                            </form>
                          </div>
                        )}
                        {items.length === 0 ? (
                          <div className="px-4 py-6">
                            {isDropIndicatorVisible(section.Id, 0) && (
                              <div className="mb-3 rounded-full bg-ui-gold-500 h-1.5 w-full" />
                            )}
                            <div className="rounded-md border border-dashed border-gray-200 px-4 py-4 text-center">
                              <p className="text-xs font-medium text-gray-500">
                                {isAcademicDatesSection
                                  ? 'No academic dates added'
                                  : 'No items in this section'}
                              </p>
                              <p className="mt-1 text-xs text-gray-400">
                                {isAcademicDatesSection
                                  ? 'Use the form above to add a Registrar deadline, or move an approved submission here.'
                                  : 'Approved submissions can be moved here before export.'}
                              </p>
                            </div>
                          </div>
                        ) : (
                          <div className="divide-y divide-gray-50">
                            {items.map((item) => {
                              const submissionIndex = item.Kind === 'submission'
                                ? submissionItems.findIndex((submissionItem) => submissionItem.Id === item.Id)
                                : -1;
                              const isDraggedItem = dragState?.itemId === item.Id;
                              const showIndicatorBefore = item.Kind === 'submission'
                                && isDropIndicatorVisible(section.Id, submissionIndex);
                              const isLastSubmission = item.Kind === 'submission'
                                && submissionIndex === submissionItems.length - 1;
                              const showIndicatorAfter = isLastSubmission
                                && isDropIndicatorVisible(section.Id, submissionItems.length);
                              return (
                                <div key={item.Id}>
                                  {showIndicatorBefore && (
                                    <div className="px-4">
                                      <div className="h-1.5 rounded-full bg-ui-gold-500" />
                                    </div>
                                  )}
                                  <div
                                    data-draggable-card={item.Kind === 'submission' ? 'true' : 'false'}
                                    data-item-kind={item.Kind}
                                    data-item-id={item.Id}
                                    data-section-id={section.Id}
                                    data-submission-index={submissionIndex >= 0 ? submissionIndex : undefined}
                                    className={`px-4 py-3 hover:bg-gray-50 group transition-opacity ${
                                      isDraggedItem ? 'opacity-25 pointer-events-none' : ''
                                    }`}
                                  >
                                    <div className="flex items-start justify-between">
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                          <p className="text-sm font-medium text-gray-900">
                                            {item.Final_Headline}
                                          </p>
                                          {item.Kind === 'calendar_event' && (
                                            <span className="inline-flex items-center rounded-full bg-ui-clearwater-100 px-2 py-0.5 text-[11px] font-medium text-ui-clearwater-800">
                                              Calendar
                                            </span>
                                          )}
                                          {item.Kind === 'job_posting' && (
                                            <span className="inline-flex items-center rounded-full bg-ui-gold-100 px-2 py-0.5 text-[11px] font-medium text-ui-gold-800">
                                              Job
                                            </span>
                                          )}
                                          {item.Kind === 'recurring_message' && (
                                            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                                              Recurring
                                            </span>
                                          )}
                                          {item.Kind === 'academic_date' && (
                                            <span className="inline-flex items-center rounded-full bg-ui-clearwater-100 px-2 py-0.5 text-[11px] font-medium text-ui-clearwater-800">
                                              Academic date
                                            </span>
                                          )}
                                        </div>
                                        <RichBody
                                          text={item.Final_Body}
                                          className="mt-2 max-w-[75ch] text-xs leading-5 text-gray-600"
                                        />
                                        {item.Kind === 'submission' && item.Run_Number > 1 && (
                                          <span className="text-xs text-ui-gold-600 mt-1 inline-block">
                                            Run #{item.Run_Number}
                                          </span>
                                        )}
                                        {item.Kind === 'calendar_event' && item.Event_Start && (
                                          <p className="text-xs text-gray-400 mt-1">
                                            {new Date(item.Event_Start).toLocaleString('en-US', {
                                              weekday: 'short',
                                              month: 'short',
                                              day: 'numeric',
                                              hour: 'numeric',
                                              minute: '2-digit',
                                            })}
                                            {item.Location ? ` • ${item.Location}` : ''}
                                          </p>
                                        )}
                                        {item.Kind === 'job_posting' && item.Location && (
                                          <p className="text-xs text-gray-400 mt-1">{item.Location}</p>
                                        )}
                                        {item.Kind === 'academic_date' && item.Source_Url && (
                                          <a
                                            href={item.Source_Url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="mt-1 inline-block text-xs text-ui-clearwater-700 hover:text-ui-clearwater-900"
                                          >
                                            View Registrar source
                                          </a>
                                        )}
                                      </div>
                                      <div className="ml-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                                        {item.Kind === 'submission' && (
                                          <>
                                            <button
                                              type="button"
                                              onClick={() => beginNewsletterItemEdit(item)}
                                              className="rounded px-2 py-1 text-xs font-medium text-ui-clearwater-700 hover:bg-ui-clearwater-50 hover:text-ui-clearwater-900"
                                              aria-label={`Edit ${item.Final_Headline}`}
                                            >
                                              Edit
                                            </button>
                                            <button
                                              type="button"
                                              onPointerDown={(event) => startSubmissionDrag(item, event)}
                                              className="cursor-grab rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 active:cursor-grabbing"
                                              title="Drag to reorder or move to another section"
                                            >
                                              &#8942;
                                            </button>
                                            <select
                                              value={item.Section_Id}
                                              onChange={(event) => void handleReassignSubmission(item.Id, event.target.value)}
                                              className="rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-600"
                                              title="Move to section"
                                            >
                                              {sections.map((targetSection) => (
                                                <option key={targetSection.Id} value={targetSection.Id}>
                                                  {targetSection.Name}
                                                </option>
                                              ))}
                                            </select>
                                            <button
                                              onClick={() => handleMoveItem(item.Id, 'up')}
                                              disabled={submissionIndex === 0}
                                              className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                                              title="Move up"
                                            >
                                              &#x25B2;
                                            </button>
                                            <button
                                              onClick={() => handleMoveItem(item.Id, 'down')}
                                              disabled={submissionIndex === submissionItems.length - 1}
                                              className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                                              title="Move down"
                                            >
                                              &#x25BC;
                                            </button>
                                          </>
                                        )}
                                        <button
                                          onClick={() => (
                                            item.Kind === 'submission'
                                              ? handleRemoveItem(item.Id)
                                              : handleRemoveExternalItem(item.Id, item.Source_Type, item.Source_Id)
                                          )}
                                          className="p-1 text-red-400 hover:text-red-600"
                                          title="Remove"
                                        >
                                          &times;
                                        </button>
                                      </div>
                                    </div>
                                    {item.Kind === 'submission' && itemEditDraft?.Item_Id === item.Id && (
                                      <form
                                        onSubmit={(event) => void handleSaveNewsletterItem(event)}
                                        className="mt-4 space-y-3 border-t border-gray-200 pt-4"
                                      >
                                        <div>
                                          <label
                                            htmlFor={`builder-item-${item.Id}-headline`}
                                            className="mb-1 block text-xs font-medium text-gray-600"
                                          >
                                            Newsletter headline
                                          </label>
                                          <input
                                            id={`builder-item-${item.Id}-headline`}
                                            type="text"
                                            value={itemEditDraft.Headline}
                                            onChange={(event) => setItemEditDraft((current) => (
                                              current ? { ...current, Headline: event.target.value } : current
                                            ))}
                                            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                                          />
                                        </div>
                                        <div>
                                          <label
                                            htmlFor={`builder-item-${item.Id}-body`}
                                            className="mb-1 block text-xs font-medium text-gray-600"
                                          >
                                            Newsletter body
                                          </label>
                                          <textarea
                                            id={`builder-item-${item.Id}-body`}
                                            value={itemEditDraft.Body}
                                            onChange={(event) => setItemEditDraft((current) => (
                                              current ? { ...current, Body: event.target.value } : current
                                            ))}
                                            rows={6}
                                            className="w-full resize-y rounded-md border border-gray-300 px-3 py-2 text-sm leading-6 focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                                          />
                                        </div>
                                        {itemEditDraft.Links.length > 0 && (
                                          <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
                                            <p className="mb-1 text-[11px] font-medium text-gray-500">
                                              Live link preview
                                            </p>
                                            <RichBody
                                              text={buildLinkedBody(itemEditDraft.Body, itemEditDraft.Links)}
                                              className="text-xs leading-5 text-gray-700"
                                            />
                                          </div>
                                        )}
                                        <div className="flex justify-end gap-2">
                                          <button
                                            type="button"
                                            onClick={() => setItemEditDraft(null)}
                                            disabled={itemEditSaving}
                                            className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                                          >
                                            Cancel
                                          </button>
                                          <button
                                            type="submit"
                                            disabled={itemEditSaving}
                                            className="rounded-md bg-ui-clearwater-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-ui-clearwater-800 disabled:opacity-50"
                                          >
                                            {itemEditSaving ? 'Saving...' : 'Save newsletter text'}
                                          </button>
                                        </div>
                                      </form>
                                    )}
                                  </div>
                                  {showIndicatorAfter && (
                                    <div className="px-4 pb-1">
                                      <div className="h-1.5 rounded-full bg-ui-gold-500" />
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Sidebar — previous newsletters */}
        <div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Recent Newsletters</h3>
            {newsletters.length === 0 ? (
              <p className="text-xs text-gray-500">No newsletters yet</p>
            ) : (
              <div className="space-y-2">
                {newsletters.map((nl) => (
                  <button
                    key={nl.Id}
                    onClick={() => handleLoadNewsletter(nl.Id)}
                    className={`w-full text-left p-2 rounded text-sm hover:bg-gray-50 ${
                      newsletter?.Id === nl.Id ? 'bg-ui-gold-50 border border-ui-gold-200' : ''
                    }`}
                  >
                    <p className="font-medium text-gray-900">
                      {parseISODate(nl.Publish_Date).toLocaleDateString()}
                    </p>
                    <p className="text-xs text-gray-500">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-xs ${STATUS_COLORS[nl.Status] || 'bg-gray-100'}`}
                      >
                        {nl.Status.replace(/_/g, ' ')}
                      </span>
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
