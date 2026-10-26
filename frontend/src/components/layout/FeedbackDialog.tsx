import { useState } from 'react';
import { createFeedback } from '../../api/feedback';
import type { FeedbackType } from '../../types/feedback';
import { Button, Modal } from '../common';
import type { FeedbackContext } from '../../utils/feedback';

const TYPE_OPTIONS: Array<{ value: FeedbackType; label: string }> = [
  { value: 'bug', label: 'Bug' },
  { value: 'idea', label: 'Feature idea' },
];

interface FeedbackDialogProps {
  open: boolean;
  context: FeedbackContext;
  onClose: () => void;
  onSubmitted?: () => void;
}

export default function FeedbackDialog({
  open,
  context,
  onClose,
  onSubmitted,
}: FeedbackDialogProps) {
  const [feedbackType, setFeedbackType] = useState<FeedbackType>('bug');
  const [summary, setSummary] = useState('');
  const [details, setDetails] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const resetAndClose = () => {
    setError(null);
    setSubmitting(false);
    onClose();
  };

  const handleSubmit = async () => {
    if (!summary.trim() || !details.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createFeedback({
        Feedback_Type: feedbackType,
        Summary: summary.trim(),
        Details: details.trim(),
        Contact_Email: contactEmail.trim() || null,
        ...context,
      });
      setFeedbackType('bug');
      setSummary('');
      setDetails('');
      setContactEmail('');
      onSubmitted?.();
      resetAndClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} title="Report a bug or feature idea" wide busy={submitting}
      description="This goes directly to the UCM Daily Register feedback queue."
      onCancel={resetAndClose}>
      <div className="mt-4 space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Type</label>
          <div className="flex gap-2">
            {TYPE_OPTIONS.map((option) => (
              <button
                key={option.value}
                aria-pressed={feedbackType === option.value}
                type="button"
                onClick={() => setFeedbackType(option.value)}
                className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
                  feedbackType === option.value
                    ? 'border-ui-gold-500 bg-ui-gold-50 text-ui-black'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="feedback-summary" className="block text-xs font-medium text-gray-500 mb-1">
            Short summary
          </label>
          <input
            data-dialog-initial-focus
            id="feedback-summary"
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            maxLength={240}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-600"
            placeholder="What should we fix or improve?"
          />
        </div>

        <div>
          <label htmlFor="feedback-details" className="block text-xs font-medium text-gray-500 mb-1">
            Details
          </label>
          <textarea
            id="feedback-details"
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            rows={5}
            maxLength={5000}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-600"
            placeholder="What were you doing? What happened? What would have helped?"
          />
        </div>

        <div>
          <label htmlFor="feedback-contact-email" className="block text-xs font-medium text-gray-500 mb-1">
            Contact email <span className="font-normal text-gray-600">(optional)</span>
          </label>
          <input
            id="feedback-contact-email"
            type="email"
            value={contactEmail}
            onChange={(event) => setContactEmail(event.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-600"
            placeholder="you@uidaho.edu"
          />
        </div>

        <p className="rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-500">
          We include page route, app mode, environment, browser, and viewport. We do not
          include submission text, submitter records, or editorial notes automatically.
          Your report and optional contact email are stored for staff review. Do not paste
          sensitive information, credentials, or private submission content here.
        </p>

        {error && (
          <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={resetAndClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={() => void handleSubmit()}
          disabled={submitting || summary.trim().length < 3 || details.trim().length < 5}
        >
          {submitting ? 'Submitting...' : 'Submit Feedback'}
        </Button>
      </div>
    </Modal>
  );
}
