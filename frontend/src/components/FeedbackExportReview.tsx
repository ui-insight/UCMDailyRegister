import { useEffect, useState } from 'react';
import { getFeedbackGitHubExportPreview, prepareFeedbackGitHubExport } from '../api/feedback';
import type { ProductFeedbackExport } from '../types/feedback';
import { buildGitHubIssueUrl } from '../utils/feedback';
import { Button } from './common';

export default function FeedbackExportReview({ feedbackId, onClose }: {
  feedbackId: string;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<ProductFeedbackExport | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [prepared, setPrepared] = useState<ProductFeedbackExport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    getFeedbackGitHubExportPreview(feedbackId).then((value) => {
      if (active) setDraft(value);
    }).catch(() => {
      if (active) setError('The export draft could not be loaded. Try again.');
    });
    return () => { active = false; };
  }, [feedbackId, attempt]);

  const change = (field: 'Title' | 'Body', value: string) => {
    setDraft((current) => current && { ...current, [field]: value });
    setConfirmed(false);
    setPrepared(null);
    setMessage('');
  };
  const prepare = async () => {
    if (!draft || !confirmed || busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await prepareFeedbackGitHubExport(feedbackId, {
        ...draft, Review_Confirmed: true,
      });
      setPrepared(result);
      setMessage('Reviewed export recorded. The original report is unchanged.');
    } catch {
      setError('The reviewed export could not be prepared. Your edits are preserved. Try again.');
    } finally {
      setBusy(false);
    }
  };
  const copy = async () => {
    if (!prepared || !confirmed) return;
    try {
      await navigator.clipboard.writeText(`${prepared.Title}\n\n${prepared.Body}`);
      setMessage('Reviewed issue text copied.');
    } catch {
      setError('Copy failed. You can still open the reviewed draft in GitHub.');
    }
  };
  const text = draft ? `${draft.Title}\n${draft.Body}` : '';
  // The only email/phone check: it re-runs on every edit. Advisory, not a redaction guarantee.
  const email = /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.test(text);
  const phone = /(?<!\w)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)/.test(text);

  return (
    <section aria-labelledby="export-review-heading" className="mt-5 border-t border-gray-200 pt-5">
      <h4 id="export-review-heading" className="font-semibold text-gray-900">Review for public sharing</h4>
      <p className="mt-2 max-w-[70ch] text-sm text-gray-700">
        Remove names, personal contact details, unpublished copy and private links from the title,
        report and diagnostic context. Only this edited copy will be shared.
      </p>
      {error && <p role="alert" className="mt-3 text-sm text-status-error-800">{error}</p>}
      {!draft ? (
        <div className="mt-3 flex gap-3">
          {error ? <Button onClick={() => { setError(''); setAttempt(attempt + 1); }}>Retry draft</Button>
            : <p role="status">Loading draft…</p>}
          <Button variant="ghost" onClick={onClose}>Cancel export</Button>
        </div>
      ) : (
        <form onSubmit={(event) => { event.preventDefault(); void prepare(); }}>
          <fieldset disabled={busy} className="mt-4 space-y-4">
            <div>
              <label htmlFor="export-review-title" className="block text-sm font-medium">Issue title</label>
              <input id="export-review-title" autoFocus required minLength={3} maxLength={255}
                value={draft.Title} onChange={(event) => change('Title', event.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2" />
            </div>
            <div>
              <label htmlFor="export-review-body" className="block text-sm font-medium">Issue body and context</label>
              <textarea id="export-review-body" required minLength={5} maxLength={12000} rows={14}
                value={draft.Body} onChange={(event) => change('Body', event.target.value)}
                aria-describedby="export-review-notice"
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div id="export-review-notice" className="text-sm text-gray-700" aria-live="polite">
              {email && <p>Possible email address in the draft. Review before sharing.</p>}
              {phone && <p>Possible phone number in the draft. Review before sharing.</p>}
              <p>These checks cannot identify every private detail. Review all text, even when no warning appears.</p>
            </div>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" checked={confirmed} className="mt-1"
                onChange={(event) => { setConfirmed(event.target.checked); setPrepared(null); }} />
              I reviewed the complete title and body and removed information that should not be public.
            </label>
            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={!confirmed || !!prepared}>
                {busy ? 'Preparing…' : 'Prepare reviewed export'}
              </Button>
              <Button type="button" variant="ghost" onClick={onClose}>Cancel export</Button>
            </div>
          </fieldset>
          <p role="status" className="mt-3 text-sm text-gray-700">{message}</p>
          {prepared && confirmed && (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button type="button" onClick={() => void copy()}>Copy reviewed text</Button>
              <a href={buildGitHubIssueUrl(prepared.Title, prepared.Body)} target="_blank" rel="noreferrer"
                className="text-sm font-medium text-ui-clearwater-800 underline">Open reviewed draft in GitHub</a>
            </div>
          )}
        </form>
      )}
    </section>
  );
}
