import { useState, type FormEvent } from 'react';
import RichBody from '../editor/RichBody';
import LinkEditor from '../submission/LinkEditor';
import OriginalEntryPanel from './OriginalEntryPanel';
import {
  buildLinkedBody,
  commitLinkLabel,
  EDITOR_MAX_LINKS,
  linkSaveProblem,
  synchronizeLinksWithBodyChange,
  type EditableBodyLink,
} from '../../utils/bodyLinks';

export interface BuilderItemEditDraft {
  Item_Id: string;
  Headline: string;
  Body: string;
  Links: EditableBodyLink[];
}

interface Props {
  itemId: string;
  submissionId: string;
  draft: BuilderItemEditDraft;
  onDraftChange: (update: (draft: BuilderItemEditDraft) => BuilderItemEditDraft) => void;
  saving: boolean;
  onCancel: () => void;
  /** Called only when every link still has words to sit on (#490). */
  onSave: () => void;
}

/**
 * Inline edit of a Builder item's wording. Links are shown and edited beside
 * the body so a link whose words were reworded or deleted is never dropped
 * without a word: saving is blocked until staff re-attach or remove it.
 */
export default function BuilderItemEditForm({
  itemId,
  submissionId,
  draft,
  onDraftChange,
  saving,
  onCancel,
  onSave,
}: Props) {
  const [linkProblem, setLinkProblem] = useState<string | null>(null);

  const update = (change: (current: BuilderItemEditDraft) => BuilderItemEditDraft) => {
    // Clear a stale warning as soon as staff act on it; Save re-checks.
    setLinkProblem(null);
    onDraftChange(change);
  };

  const handleBodyCommit = (previousBody: string, nextBody: string) => {
    update((current) => ({
      ...current,
      Links: synchronizeLinksWithBodyChange(previousBody, nextBody, current.Links),
    }));
  };

  const handleAnchorCommit = (index: number, previousValue: string, nextValue: string) => {
    update((current) => {
      const link = current.Links[index] ?? { Url: '', Anchor_Text: '' };
      const result = commitLinkLabel(current.Body, { ...link, Anchor_Text: previousValue }, nextValue);
      return {
        ...current,
        Body: result.body,
        Links: current.Links.map((candidate, candidateIndex) => (
          candidateIndex === index ? { ...candidate, Start: result.link.Start } : candidate
        )),
      };
    });
  };

  // Put a link's missing words back at the end of the body, as on the Edit
  // page (#397, #521).
  const handleRestoreWords = (index: number) => {
    handleAnchorCommit(index, '', draft.Links[index]?.Anchor_Text ?? '');
  };

  const handleMentionChange = (index: number, start: number) => {
    update((current) => ({
      ...current,
      Links: current.Links.map((link, linkIndex) => (
        linkIndex === index ? { ...link, Start: start } : link
      )),
    }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const problem = linkSaveProblem(draft.Body, draft.Links);
    setLinkProblem(problem);
    if (!problem) onSave();
  };

  return (
    <form onSubmit={handleSubmit} className="mt-4 space-y-3 border-t border-gray-200 pt-4">
      <OriginalEntryPanel submissionId={submissionId} />
      <div>
        <label
          htmlFor={`builder-item-${itemId}-headline`}
          className="mb-1 block text-xs font-medium text-gray-600"
        >
          Newsletter headline
        </label>
        <input
          id={`builder-item-${itemId}-headline`}
          type="text"
          value={draft.Headline}
          onChange={(event) => {
            const headline = event.target.value;
            update((current) => ({ ...current, Headline: headline }));
          }}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
        />
      </div>
      <div>
        <label
          htmlFor={`builder-item-${itemId}-body`}
          className="mb-1 block text-xs font-medium text-gray-600"
        >
          Newsletter body
        </label>
        <textarea
          id={`builder-item-${itemId}-body`}
          value={draft.Body}
          onFocus={(event) => {
            event.currentTarget.dataset.initialValue = event.currentTarget.value;
          }}
          onChange={(event) => {
            const body = event.target.value;
            update((current) => ({ ...current, Body: body }));
          }}
          onBlur={(event) => handleBodyCommit(
            event.currentTarget.dataset.initialValue ?? '',
            event.currentTarget.value,
          )}
          rows={6}
          className="w-full resize-y rounded-md border border-gray-300 px-3 py-2 text-sm leading-6 focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
        />
      </div>
      <div className="rounded-md border border-gray-200 bg-white px-3 py-3">
        <LinkEditor
          links={draft.Links}
          onChange={(links) => update((current) => ({ ...current, Links: links }))}
          onAnchorCommit={handleAnchorCommit}
          body={draft.Body}
          onMentionChange={handleMentionChange}
          onRestoreWords={handleRestoreWords}
          allowAddRemove
          maxLinks={EDITOR_MAX_LINKS}
          label="Links"
          description="Each link sits on words in the body. If you reword or delete those words, change the link text to words that are there, or remove the link."
        />
      </div>
      {draft.Links.some((link) => link.Url.trim()) && (
        <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
          <p className="mb-1 text-[11px] font-medium text-gray-500">
            Live link preview
          </p>
          <RichBody
            text={buildLinkedBody(draft.Body, draft.Links)}
            className="text-xs leading-5 text-gray-700"
          />
        </div>
      )}
      {linkProblem && (
        <p
          role="alert"
          className="rounded-md border border-status-warning-500/50 bg-status-warning-100/60 px-3 py-2 text-xs text-status-warning-800"
        >
          {linkProblem}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-ui-clearwater-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-ui-clearwater-800 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save newsletter text'}
        </button>
      </div>
    </form>
  );
}
