import { useId } from 'react';
import FieldError from '../common/FieldError';
import { fieldErrorProps, type FieldErrors } from '../../utils/formValidation';
import {
  findMentions,
  isSafeLinkDestination,
  looksLikeWebAddress,
  resolvedLinkStart,
} from '../../utils/bodyLinks';

export interface LinkEntry {
  Url: string;
  Anchor_Text: string;
  /** Offset of the chosen mention in `body`; see EditableBodyLink.Start. */
  Start?: number;
}

interface Props {
  errors?: FieldErrors;
  links: LinkEntry[];
  onChange: (links: LinkEntry[]) => void;
  onAnchorCommit?: (index: number, previousValue: string, nextValue: string) => void;
  /**
   * The plain body these links attach to. When given, each link shows where
   * its words are and, if they appear more than once, which mention to link.
   */
  body?: string;
  onMentionChange?: (index: number, start: number) => void;
  /**
   * Show only the links given, with Add and Remove buttons, instead of a
   * fixed set of slots. Staff use this on the Edit page (#505).
   */
  allowAddRemove?: boolean;
  /** Most links allowed. Submitters get three. */
  maxLinks?: number;
  label?: string;
  description?: string;
}

const MAX_LINKS = 3;
const CONTEXT_CHARS = 28;
const ORDINALS = ['1st', '2nd', '3rd'];

function ordinal(n: number): string {
  return ORDINALS[n - 1] ?? `${n}th`;
}

/** "…words before [linked words] words after…" for one mention. */
function mentionContext(body: string, start: number, length: number): string {
  const from = Math.max(0, start - CONTEXT_CHARS);
  const to = Math.min(body.length, start + length + CONTEXT_CHARS);
  const clean = (text: string) => text.replace(/\s+/g, ' ');
  let before = body.slice(from, start);
  let after = body.slice(start + length, to);
  // Show whole words only at the cut edges.
  if (from > 0 && !/\s/.test(body[from - 1])) before = before.replace(/^\S*/, '');
  if (to < body.length && !/\s/.test(body[to])) after = after.replace(/\S*$/, '');
  return [
    from > 0 ? '…' : '',
    clean(before).trimStart(),
    `[${clean(body.slice(start, start + length))}]`,
    clean(after).trimEnd(),
    to < body.length ? '…' : '',
  ].join('');
}

function hasDestination(url: string): boolean {
  const trimmed = url.trim();
  return Boolean(trimmed) && trimmed !== 'mailto:';
}

function ensureSlots(links: LinkEntry[], maxLinks: number): LinkEntry[] {
  const slots = [...links];
  while (slots.length < maxLinks) {
    slots.push({ Url: '', Anchor_Text: '' });
  }
  return slots.slice(0, maxLinks);
}

export default function LinkEditor({
  errors = {},
  links,
  onChange,
  onAnchorCommit,
  body,
  onMentionChange,
  allowAddRemove = false,
  maxLinks = MAX_LINKS,
  label = 'Links to Embed',
  description = `Add up to ${MAX_LINKS} web URLs or email addresses to embed in your announcement.`,
}: Props) {
  const descriptionId = useId();
  // Never hide a link the caller already has: it would be dropped on save.
  const slots = allowAddRemove ? links : ensureSlots(links, maxLinks);

  const updateLink = (index: number, field: keyof LinkEntry, value: string) => {
    const updated = slots.map((link, i) =>
      i === index ? { ...link, [field]: value } : link,
    );
    onChange(updated);
  };

  const removeLink = (index: number) => {
    onChange(slots.filter((_, i) => i !== index));
  };

  const addLink = () => {
    onChange([...slots, { Url: '', Anchor_Text: '' }]);
  };

  return (
    <div role="group" aria-label={label}>
      <p className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </p>
      <p id={descriptionId} className="text-xs text-gray-500 mb-3">
        {description}
      </p>
      <div className="space-y-3">
        {slots.map((link, index) => (
          <LinkRow
            key={index}
            index={index}
            link={link}
            errors={errors}
            descriptionId={descriptionId}
            body={body}
            onUpdate={updateLink}
            onRemove={allowAddRemove ? removeLink : undefined}
            onAnchorCommit={onAnchorCommit}
            onMentionChange={onMentionChange}
          />
        ))}
        {allowAddRemove && slots.length === 0 && (
          <p className="text-xs text-gray-500">No links yet.</p>
        )}
      </div>
      {allowAddRemove && slots.length < maxLinks && (
        <button
          type="button"
          onClick={addLink}
          className="mt-3 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          Add a link
        </button>
      )}
    </div>
  );
}

/** Detect whether a slot is storing a mailto: link. */
function isEmailLink(url: string): boolean {
  return url.startsWith('mailto:');
}

function LinkRow({
  index,
  link,
  errors,
  descriptionId,
  body,
  onUpdate,
  onRemove,
  onAnchorCommit,
  onMentionChange,
}: {
  index: number;
  link: LinkEntry;
  errors: FieldErrors;
  descriptionId: string;
  body?: string;
  onUpdate: (index: number, field: keyof LinkEntry, value: string) => void;
  onRemove?: (index: number) => void;
  onAnchorCommit?: (index: number, previousValue: string, nextValue: string) => void;
  onMentionChange?: (index: number, start: number) => void;
}) {
  const emailMode = isEmailLink(link.Url);

  /** Toggle between web URL and email mode for a slot. */
  const toggleLinkType = () => {
    // Web clears the address; email starts an empty mailto: address.
    onUpdate(index, 'Url', emailMode ? '' : 'mailto:');
  };

  const handleEmailChange = (email: string) => {
    // A pasted web address turns this into a web link rather than a broken
    // mailto: link that would be dropped on save (#505).
    onUpdate(index, 'Url', looksLikeWebAddress(email) ? email.trim() : `mailto:${email}`);
  };

  const urlId = `submission-link-${index}-url`;
  const anchorId = `submission-link-${index}-anchor`;
  const inputClass = 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500';
  const badDestination = body !== undefined
    && hasDestination(link.Url)
    && !isSafeLinkDestination(link.Url);

  return (
    <div role="group" aria-label={`Link ${index + 1}`} className="rounded-md border border-gray-200 bg-gray-50 p-3">
      <div className="flex items-center justify-between gap-3 mb-2">
        <p className="text-xs font-medium text-gray-500">Link {index + 1}</p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleLinkType}
            className="text-xs text-ui-gold-800 hover:text-ui-gold-800 font-medium"
          >
            {emailMode ? 'Switch to web link' : 'Switch to email link'}
          </button>
          {onRemove && (
            <button
              type="button"
              onClick={() => onRemove(index)}
              aria-label={`Remove link ${index + 1}`}
              className="text-xs font-medium text-gray-600 hover:text-gray-800"
            >
              Remove
            </button>
          )}
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div>
          <label htmlFor={urlId} className="block text-xs text-gray-500 mb-1">
            {emailMode ? 'Email address' : 'URL'}
          </label>
          {emailMode ? (
            <input
              id={urlId}
              {...fieldErrorProps(errors, urlId, descriptionId)}
              type="email"
              placeholder="name@uidaho.edu"
              value={link.Url.replace(/^mailto:/, '')}
              onChange={(e) => handleEmailChange(e.target.value)}
              autoComplete="off"
              className={inputClass}
            />
          ) : (
            <input
              id={urlId}
              {...fieldErrorProps(errors, urlId, descriptionId)}
              type="url"
              placeholder="https://..."
              value={link.Url}
              onChange={(e) => onUpdate(index, 'Url', e.target.value)}
              autoComplete="off"
              className={inputClass}
            />
          )}
        </div>
        <div>
          <label htmlFor={anchorId} className="block text-xs text-gray-500 mb-1">
            {emailMode
              ? "Link text (person's name or email address)"
              : 'Words to link the URL to (e.g., Learn more.)'}
          </label>
          <input
            id={anchorId}
            {...fieldErrorProps(errors, anchorId, descriptionId)}
            type="text"
            placeholder={emailMode ? 'e.g., Jane Smith' : 'e.g., Learn more'}
            value={link.Anchor_Text}
            onFocus={(e) => {
              e.currentTarget.dataset.initialValue = e.currentTarget.value;
            }}
            onChange={(e) => onUpdate(index, 'Anchor_Text', e.target.value)}
            onBlur={(e) => onAnchorCommit?.(
              index,
              e.currentTarget.dataset.initialValue ?? '',
              e.currentTarget.value,
            )}
            autoComplete="off"
            className={inputClass}
          />
        </div>
      </div>
      <FieldError errors={errors} id={urlId} />
      <FieldError errors={errors} id={anchorId} />
      {badDestination && (
        <p className="mt-2 text-xs text-status-warning-800">
          {emailMode
            ? "This isn't a complete email address, so this link can't be saved."
            : "Web links must start with https://, so this link can't be saved."}
        </p>
      )}
      {body !== undefined && link.Anchor_Text.trim() && (
        <LinkPlacement
          index={index}
          body={body}
          link={link}
          onMentionChange={onMentionChange}
        />
      )}
      {emailMode && (
        <p className="text-[11px] text-gray-600 mt-1.5">
          For individual email addresses, use the person's name as the link text. For general addresses, the email address itself is fine.
        </p>
      )}
    </div>
  );
}

function LinkPlacement({
  index,
  body,
  link,
  onMentionChange,
}: {
  index: number;
  body: string;
  link: LinkEntry;
  onMentionChange?: (index: number, start: number) => void;
}) {
  const words = link.Anchor_Text.trim();
  const mentions = findMentions(body, words);
  const current = resolvedLinkStart(body, link);

  if (mentions.length === 0) {
    return hasDestination(link.Url) ? (
      <p role="status" className="mt-2 text-xs text-status-warning-800">
        These words aren&apos;t in the body, so this link can&apos;t be saved. Add them to the body,
        or change them to words that are there.
      </p>
    ) : null;
  }

  if (mentions.length === 1) {
    return (
      <p className="mt-2 text-[11px] text-gray-500">
        Linked text: {mentionContext(body, mentions[0], words.length)}
      </p>
    );
  }

  const selectId = `submission-link-${index}-mention`;
  return (
    <div className="mt-2">
      <label htmlFor={selectId} className="block text-xs text-gray-500 mb-1">
        These words appear {mentions.length} times. Which one gets the link?
      </label>
      <select
        id={selectId}
        value={current ?? mentions[0]}
        onChange={(e) => onMentionChange?.(index, Number(e.target.value))}
        className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
      >
        {mentions.map((start, mentionIndex) => (
          <option key={start} value={start}>
            {ordinal(mentionIndex + 1)}: {mentionContext(body, start, words.length)}
          </option>
        ))}
      </select>
    </div>
  );
}
