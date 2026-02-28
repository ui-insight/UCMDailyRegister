import { useEffect, useState } from 'react';
import {
  listNewsletters,
  getNewsletter,
  assembleNewsletter,
  updateNewsletterStatus,
  removeNewsletterItem,
  reorderNewsletterItems,
  getExportUrl,
  listSections,
} from '../api/newsletters';
import type { NewsletterDetailResponse, NewsletterItemResponse } from '../api/newsletters';
import type { NewsletterSection } from '../types/newsletter';

export default function BuilderPage() {
  const [newsletterType, setNewsletterType] = useState<'tdr' | 'myui'>('tdr');
  const [publishDate, setPublishDate] = useState(
    new Date().toISOString().split('T')[0],
  );
  const [newsletter, setNewsletter] = useState<NewsletterDetailResponse | null>(null);
  const [newsletters, setNewsletters] = useState<NewsletterDetailResponse[]>([]);
  const [sections, setSections] = useState<NewsletterSection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    loadSections();
    loadNewsletters();
  }, [newsletterType]);

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

  // Group items by section
  const sectionMap = new Map<string, NewsletterSection>();
  sections.forEach((s) => sectionMap.set(s.Id, s));

  const itemsBySection = new Map<string, NewsletterItemResponse[]>();
  if (newsletter) {
    for (const section of sections) {
      const items = newsletter.Items
        .filter((i) => i.Section_Id === section.Id)
        .sort((a, b) => a.Position - b.Position);
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
                    {newsletter.Items.length} item{newsletter.Items.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>

              {/* Sections with items */}
              {sections.map((section) => {
                const items = itemsBySection.get(section.Id) || [];
                return (
                  <div key={section.Id} className="bg-white rounded-lg shadow">
                    <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-gray-900">
                        {section.Name}
                      </h4>
                      <span className="text-xs text-gray-400">
                        {items.length} item{items.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    {items.length === 0 ? (
                      <div className="px-4 py-6 text-center text-xs text-gray-400">
                        No items in this section
                      </div>
                    ) : (
                      <div className="divide-y divide-gray-50">
                        {items.map((item, idx) => (
                          <div
                            key={item.Id}
                            className="px-4 py-3 hover:bg-gray-50 group"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900">
                                  {item.Final_Headline}
                                </p>
                                <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                  {item.Final_Body.replace(/<[^>]+>/g, '')}
                                </p>
                                {item.Run_Number > 1 && (
                                  <span className="text-xs text-ui-gold-600 mt-1 inline-block">
                                    Run #{item.Run_Number}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
                                <button
                                  onClick={() => handleMoveItem(item.Id, 'up')}
                                  disabled={idx === 0}
                                  className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                                  title="Move up"
                                >
                                  &#x25B2;
                                </button>
                                <button
                                  onClick={() => handleMoveItem(item.Id, 'down')}
                                  disabled={idx === items.length - 1}
                                  className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                                  title="Move down"
                                >
                                  &#x25BC;
                                </button>
                                <button
                                  onClick={() => handleRemoveItem(item.Id)}
                                  className="p-1 text-red-400 hover:text-red-600"
                                  title="Remove"
                                >
                                  &times;
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
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
