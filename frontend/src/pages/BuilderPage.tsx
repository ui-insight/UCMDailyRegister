import { useEffect, useRef, useState, type DragEvent, type ReactNode } from 'react';
import {
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
} from '../api/newsletters';
import type {
  CalendarEventCandidate,
  JobPostingCandidate,
  NewsletterDetailResponse,
  NewsletterItemResponse,
} from '../api/newsletters';
import type { NewsletterSection } from '../types/newsletter';

interface BuilderSectionItemBase {
  Id: string;
  Section_Id: string;
  Position: number;
  Final_Headline: string;
  Final_Body: string;
}

type BuilderSectionItem =
  | (BuilderSectionItemBase & { Kind: 'submission'; Run_Number: number })
  | (BuilderSectionItemBase & {
    Kind: 'calendar_event';
    Source_Url: string | null;
    Location: string | null;
    Event_Start: string | null;
    Source_Type: string;
  })
  | (BuilderSectionItemBase & {
    Kind: 'job_posting';
    Source_Url: string | null;
    Location: string | null;
    Posting_Number?: string | null;
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

function isSubmissionItem(
  item: BuilderSectionItem,
): item is BuilderSectionItemBase & { Kind: 'submission'; Run_Number: number } {
  return item.Kind === 'submission';
}

function buildSubmissionReorderPayload(
  newsletter: NewsletterDetailResponse,
  sections: NewsletterSection[],
  itemId: string,
  targetSectionId: string,
  targetIndex: number,
): { Id: string; Position: number; Section_Id: string }[] | null {
  const sectionOrder = new Map(sections.map((section, index) => [section.Id, index]));
  const itemsBySection = new Map<string, NewsletterItemResponse[]>(
    sections.map((section) => [section.Id, []]),
  );

  const orderedItems = [...newsletter.Items].sort((a, b) => {
    const sectionDiff =
      (sectionOrder.get(a.Section_Id) ?? Number.MAX_SAFE_INTEGER)
      - (sectionOrder.get(b.Section_Id) ?? Number.MAX_SAFE_INTEGER);
    if (sectionDiff !== 0) return sectionDiff;
    return a.Position - b.Position || a.Final_Headline.localeCompare(b.Final_Headline);
  });

  for (const item of orderedItems) {
    const sectionItems = itemsBySection.get(item.Section_Id);
    if (sectionItems) {
      sectionItems.push({ ...item });
    }
  }

  const draggedItem = orderedItems.find((item) => item.Id === itemId);
  if (!draggedItem) return null;

  const sourceItems = itemsBySection.get(draggedItem.Section_Id);
  const targetItems = itemsBySection.get(targetSectionId);
  if (!sourceItems || !targetItems) return null;

  const sourceIndex = sourceItems.findIndex((item) => item.Id === itemId);
  if (sourceIndex === -1) return null;

  const [movedItem] = sourceItems.splice(sourceIndex, 1);
  let insertIndex = Math.max(0, Math.min(targetIndex, targetItems.length));

  if (draggedItem.Section_Id === targetSectionId && insertIndex > sourceIndex) {
    insertIndex -= 1;
  }

  if (draggedItem.Section_Id === targetSectionId && insertIndex === sourceIndex) {
    return null;
  }

  targetItems.splice(insertIndex, 0, {
    ...movedItem,
    Section_Id: targetSectionId,
  });

  const payload: { Id: string; Position: number; Section_Id: string }[] = [];
  for (const section of sections) {
    const sectionItems = itemsBySection.get(section.Id) ?? [];
    for (const [index, item] of sectionItems.entries()) {
      payload.push({
        Id: item.Id,
        Position: index,
        Section_Id: section.Id,
      });
    }
  }

  return payload;
}

export default function BuilderPage() {
  const [newsletterType, setNewsletterType] = useState<'tdr' | 'myui'>('tdr');
  const [publishDate, setPublishDate] = useState(
    new Date().toISOString().split('T')[0],
  );
  const [newsletter, setNewsletter] = useState<NewsletterDetailResponse | null>(null);
  const [newsletters, setNewsletters] = useState<NewsletterDetailResponse[]>([]);
  const [sections, setSections] = useState<NewsletterSection[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEventCandidate[]>([]);
  const [jobPostings, setJobPostings] = useState<JobPostingCandidate[]>([]);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarError, setCalendarError] = useState<string | null>(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState({
    calendarEvents: true,
    jobPostings: true,
  });
  const [sectionOpen, setSectionOpen] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [draggedSubmissionId, setDraggedSubmissionId] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<{ sectionId: string; index: number } | null>(null);
  const [reordering, setReordering] = useState(false);
  const hoverExpandTimeoutRef = useRef<number | null>(null);
  const hoverExpandSectionRef = useRef<string | null>(null);
  const newsletterId = newsletter?.Id;

  useEffect(() => {
    loadSections();
    loadNewsletters();
  }, [newsletterType]);

  useEffect(() => {
    if (!newsletterId) {
      setCalendarEvents([]);
      setCalendarError(null);
      setJobPostings([]);
      setJobError(null);
      return;
    }
    loadCalendarEvents(newsletterId);
    loadJobPostings(newsletterId);
  }, [newsletterId]);

  const loadSections = async () => {
    try {
      const secs = await listSections(newsletterType);
      setSections(secs);
    } catch (err) {
      console.error('Failed to load sections:', err);
    }
  };

  const loadNewsletters = async () => {
    try {
      const list = await listNewsletters({ newsletter_type: newsletterType });
      setNewsletters(list as NewsletterDetailResponse[]);
    } catch (err) {
      console.error('Failed to load newsletters:', err);
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

  const handleRemoveExternalItem = async (itemId: string) => {
    if (!newsletter) return;
    try {
      await removeNewsletterExternalItem(newsletter.Id, itemId);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
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

  const showToast = (message: string) => {
    setToast(message);
    setTimeout(() => setToast(null), 3000);
  };

  const togglePanel = (panel: 'calendarEvents' | 'jobPostings') => {
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

  const clearHoverExpandTimeout = () => {
    if (hoverExpandTimeoutRef.current !== null) {
      window.clearTimeout(hoverExpandTimeoutRef.current);
      hoverExpandTimeoutRef.current = null;
    }
    hoverExpandSectionRef.current = null;
  };

  const queueSectionExpand = (sectionId: string, isOpen: boolean) => {
    if (isOpen || hoverExpandSectionRef.current === sectionId) return;
    clearHoverExpandTimeout();
    hoverExpandSectionRef.current = sectionId;
    hoverExpandTimeoutRef.current = window.setTimeout(() => {
      setSectionOpen((current) => ({
        ...current,
        [sectionId]: true,
      }));
      clearHoverExpandTimeout();
    }, 300);
  };

  const resetDragState = () => {
    clearHoverExpandTimeout();
    setDraggedSubmissionId(null);
    setDropTarget(null);
  };

  const handleDragStart = (event: DragEvent<HTMLDivElement>, itemId: string) => {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', itemId);
    setDraggedSubmissionId(itemId);
  };

  const handleDragOver = (
    event: DragEvent<HTMLElement>,
    sectionId: string,
    index: number,
    sectionIsOpen: boolean,
  ) => {
    event.preventDefault();
    if (!draggedSubmissionId) return;
    event.dataTransfer.dropEffect = 'move';
    queueSectionExpand(sectionId, sectionIsOpen);
    setDropTarget((current) => (
      current?.sectionId === sectionId && current.index === index
        ? current
        : { sectionId, index }
    ));
  };

  const handleDrop = async (
    event: DragEvent<HTMLElement>,
    sectionId: string,
    index: number,
  ) => {
    event.preventDefault();
    if (!newsletter || !draggedSubmissionId) {
      resetDragState();
      return;
    }

    const positions = buildSubmissionReorderPayload(
      newsletter,
      sections,
      draggedSubmissionId,
      sectionId,
      index,
    );

    if (!positions) {
      resetDragState();
      return;
    }

    try {
      setReordering(true);
      await reorderNewsletterItems(newsletter.Id, positions);
      const nl = await getNewsletter(newsletter.Id);
      setNewsletter(nl);
      showToast('Submission moved');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reorder');
    } finally {
      setReordering(false);
      resetDragState();
    }
  };

  useEffect(() => () => {
    clearHoverExpandTimeout();
  }, []);

  // Group items by section
  const itemsBySection = new Map<string, BuilderSectionItem[]>();
  if (newsletter) {
    const submissionItems: BuilderSectionItem[] = newsletter.Items.map((item) => ({
      ...item,
      Kind: 'submission',
    }));
    const externalItems: BuilderSectionItem[] = newsletter.External_Items.map((item) => ({
      Id: item.Id,
      Section_Id: item.Section_Id,
      Position: item.Position,
      Final_Headline: item.Final_Headline,
      Final_Body: item.Final_Body,
      Kind: item.Source_Type === 'job_posting' ? 'job_posting' : 'calendar_event',
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
    }
  }

  const STATUS_COLORS: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-800',
    in_progress: 'bg-blue-100 text-blue-800',
    ready_for_review: 'bg-yellow-100 text-yellow-800',
    submitted: 'bg-ui-clearwater-100 text-ui-clearwater-800',
    published: 'bg-green-100 text-green-800',
  };

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          {toast}
        </div>
      )}

      <h2 className="text-2xl font-bold text-gray-900 mb-6">Newsletter Builder</h2>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Newsletter</label>
            <select
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
            <label className="block text-xs text-gray-500 mb-1">Publish Date</label>
            <input
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
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <p className="text-gray-500">
                Select a newsletter type and date, then click "Assemble Newsletter"
                to auto-populate from approved submissions.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <CollapsibleCard
                title="Calendar Events"
                subtitle={`Import upcoming U of I calendar events into the ${
                  newsletterType === 'tdr' ? "Today's Events" : 'Weekly Events'
                } section.`}
                meta={`${calendarEvents.length} candidate${calendarEvents.length !== 1 ? 's' : ''}`}
                isOpen={panelOpen.calendarEvents}
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
                  <div className="rounded-md border border-dashed border-gray-200 px-4 py-6 text-center text-xs text-gray-400">
                    {calendarLoading ? 'Loading candidate events...' : 'No candidate events found for this issue window.'}
                  </div>
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

              <CollapsibleCard
                title="Job Postings"
                subtitle={`Import U of I job postings into the ${
                  newsletterType === 'tdr' ? 'Job Opportunities' : 'Help Wanted'
                } section.`}
                meta={`${jobPostings.length} candidate${jobPostings.length !== 1 ? 's' : ''}`}
                isOpen={panelOpen.jobPostings}
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
                  <div className="rounded-md border border-dashed border-gray-200 px-4 py-6 text-center text-xs text-gray-400">
                    {jobLoading ? 'Loading job postings...' : 'No candidate job postings found.'}
                  </div>
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

              {/* Newsletter header */}
              <div className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">
                    {newsletterType === 'tdr' ? 'The Daily Register' : 'My UI'}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {new Date(newsletter.Publish_Date).toLocaleDateString('en-US', {
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

              <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-3 text-xs text-gray-600">
                Drag approved submission cards between section buckets to reclassify them or reorder them.
                Imported calendar events and job postings stay fixed for now.
              </div>

              {draggedSubmissionId && (
                <div className="rounded-lg bg-ui-gold-50 px-4 py-2 text-xs font-medium text-ui-gold-800">
                  Dragging submission. Hover over a collapsed section to open it, then drop where you want it to land.
                </div>
              )}

              {/* Sections with items */}
              {sections.map((section) => {
                const items = itemsBySection.get(section.Id) || [];
                const submissionItems = items.filter(isSubmissionItem);
                const importedItems = items.filter((item) => !isSubmissionItem(item));
                const isOpen = sectionOpen[section.Id] ?? true;
                const showDropHint = draggedSubmissionId !== null;
                const activeDropIndex =
                  dropTarget?.sectionId === section.Id ? dropTarget.index : null;
                return (
                  <div
                    key={section.Id}
                    className={`bg-white rounded-lg shadow transition-all ${
                      dropTarget?.sectionId === section.Id
                        ? 'ring-2 ring-ui-gold-200 shadow-md'
                        : ''
                    }`}
                    onDragOver={(event) => {
                      if (!showDropHint) return;
                      event.preventDefault();
                      if (!isOpen) {
                        queueSectionExpand(section.Id, isOpen);
                        setDropTarget({ sectionId: section.Id, index: submissionItems.length });
                      }
                    }}
                  >
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
                      items.length === 0 ? (
                        <div
                          className={`px-4 py-6 text-center text-xs transition-colors ${
                            showDropHint && activeDropIndex === 0
                              ? 'bg-ui-gold-50 text-ui-gold-700'
                              : 'text-gray-400'
                          }`}
                          onDragOver={(event) => handleDragOver(event, section.Id, 0, isOpen)}
                          onDrop={(event) => void handleDrop(event, section.Id, 0)}
                        >
                          {showDropHint ? 'Drop here to place the submission in this section' : 'No items in this section'}
                        </div>
                      ) : (
                        <div className="space-y-3 px-4 py-3">
                          <div
                            className={`rounded-md border border-dashed px-3 py-2 text-xs transition-colors ${
                              showDropHint
                                ? activeDropIndex === 0
                                  ? 'border-ui-gold-300 bg-ui-gold-50 text-ui-gold-700 opacity-100'
                                  : 'border-gray-200 bg-gray-50 text-gray-400 opacity-100'
                                : 'border-transparent bg-transparent text-transparent opacity-0 py-0 h-0 overflow-hidden pointer-events-none'
                            }`}
                            onDragOver={(event) => handleDragOver(event, section.Id, 0, isOpen)}
                            onDrop={(event) => void handleDrop(event, section.Id, 0)}
                          >
                            {submissionItems.length === 0
                              ? 'Drop a submission here'
                              : 'Drop here to place a submission at the top'}
                          </div>

                          {submissionItems.map((item, idx) => (
                            <div key={item.Id} className="space-y-3">
                              <div
                                draggable={!reordering}
                                onDragStart={(event) => handleDragStart(event, item.Id)}
                                onDragEnd={resetDragState}
                                className={`rounded-lg border px-4 py-3 group transition-shadow ${
                                  draggedSubmissionId === item.Id
                                    ? 'border-ui-gold-300 bg-ui-gold-50 shadow-sm'
                                    : 'border-gray-200 bg-white hover:border-ui-gold-200 hover:shadow-sm'
                                } ${reordering ? 'cursor-wait opacity-70' : 'cursor-grab active:cursor-grabbing'}`}
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span
                                        className={`tracking-[-0.2em] ${
                                          draggedSubmissionId === item.Id ? 'text-ui-gold-500' : 'text-gray-300'
                                        }`}
                                        aria-hidden="true"
                                      >
                                        ::
                                      </span>
                                      <p className="text-sm font-medium text-gray-900">
                                        {item.Final_Headline}
                                      </p>
                                    </div>
                                    <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                      {item.Final_Body.replace(/<[^>]+>/g, '')}
                                    </p>
                                    {item.Run_Number > 1 && (
                                      <span className="text-xs text-ui-gold-600 mt-1 inline-block">
                                        Run #{item.Run_Number}
                                      </span>
                                    )}
                                  </div>
                                  <button
                                    onClick={() => handleRemoveItem(item.Id)}
                                    className="p-1 text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                    title="Remove"
                                  >
                                    &times;
                                  </button>
                                </div>
                              </div>

                              <div
                                className={`rounded-md border border-dashed px-3 py-2 text-xs transition-colors ${
                                  showDropHint
                                    ? activeDropIndex === idx + 1
                                      ? 'border-ui-gold-300 bg-ui-gold-50 text-ui-gold-700 opacity-100'
                                      : 'border-gray-200 bg-gray-50 text-gray-400 opacity-100'
                                    : 'border-transparent bg-transparent text-transparent opacity-0 py-0 h-0 overflow-hidden pointer-events-none'
                                }`}
                                onDragOver={(event) => handleDragOver(event, section.Id, idx + 1, isOpen)}
                                onDrop={(event) => void handleDrop(event, section.Id, idx + 1)}
                              >
                                Drop here
                              </div>
                            </div>
                          ))}

                          {importedItems.length > 0 && (
                            <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                                Imported Items
                              </p>
                              <div className="mt-3 space-y-2">
                                {importedItems.map((item) => (
                                  <div
                                    key={item.Id}
                                    className="rounded-lg border border-gray-200 bg-white px-4 py-3"
                                  >
                                    <div className="flex items-start justify-between gap-3">
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
                                        </div>
                                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                          {item.Final_Body.replace(/<[^>]+>/g, '')}
                                        </p>
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
                                      </div>
                                      <button
                                        onClick={() => handleRemoveExternalItem(item.Id)}
                                        className="p-1 text-red-400 hover:text-red-600"
                                        title="Remove"
                                      >
                                        &times;
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )
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
                      {new Date(nl.Publish_Date).toLocaleDateString()}
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
