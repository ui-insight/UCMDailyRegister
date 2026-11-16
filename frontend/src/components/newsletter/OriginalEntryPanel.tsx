import { useId, useState } from 'react';
import { getSubmission } from '../../api/submissions';
import type { Submission } from '../../types/submission';
import OriginalSubmissionFields from '../editor/OriginalSubmissionFields';
import ScheduleRequestSummary from '../editor/ScheduleRequestSummary';

interface OriginalEntryPanelProps {
  submissionId: string;
}

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'loaded'; submission: Submission }
  | { status: 'error'; message: string };

function OriginalEntryBody({ submission }: { submission: Submission }) {
  return (
    <div className="space-y-3">
      <OriginalSubmissionFields submission={submission} />
      <div>
        <p className="mb-1 text-xs font-medium text-gray-500">Requested schedule</p>
        {submission.Schedule_Requests.length > 0 ? (
          <ul className="space-y-2">
            {submission.Schedule_Requests.map((request) => (
              <li key={request.Id} className="text-sm font-medium text-gray-900">
                <ScheduleRequestSummary
                  request={request}
                  targetNewsletter={submission.Target_Newsletter}
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-700">No dates requested</p>
        )}
      </div>
    </div>
  );
}

/**
 * "View original entry" disclosure for the Builder's item edit form. Shows the
 * submitter's original headline, body, links and requested schedule so the
 * editor can compare them with the edition copy. The submission is fetched the
 * first time the panel opens because the newsletter response carries only the
 * edition text.
 */
export default function OriginalEntryPanel({ submissionId }: OriginalEntryPanelProps) {
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<LoadState>({ status: 'idle' });

  const load = async () => {
    setState({ status: 'loading' });
    try {
      const submission = await getSubmission(submissionId);
      setState({ status: 'loaded', submission });
    } catch (err) {
      setState({
        status: 'error',
        message: err instanceof Error ? err.message : 'Could not load the original entry',
      });
    }
  };

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && (state.status === 'idle' || state.status === 'error')) {
      void load();
    }
  };

  return (
    <div className="rounded-md border border-gray-200">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          aria-controls={panelId}
          className="flex items-center gap-1 rounded text-xs font-medium text-ui-clearwater-700 hover:text-ui-clearwater-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-gold-500"
        >
          <span aria-hidden="true">{open ? '▾' : '▸'}</span>
          {open ? 'Hide original entry' : 'View original entry'}
        </button>
        <a
          href={`/edit/${submissionId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded text-xs font-medium text-ui-clearwater-700 underline hover:text-ui-clearwater-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-gold-500"
        >
          Open full submission<span className="sr-only"> (opens in a new tab)</span>
        </a>
      </div>
      <section
        id={panelId}
        hidden={!open}
        aria-label="Original entry"
        aria-busy={state.status === 'loading'}
        className="max-h-96 overflow-y-auto border-t border-gray-200 bg-gray-50 px-3 py-3"
      >
        <p className="mb-2 text-xs text-gray-500">Read-only: what the submitter sent</p>
        {state.status === 'loading' && (
          <p role="status" className="text-sm text-gray-600">Loading original entry...</p>
        )}
        {state.status === 'error' && (
          <div role="alert" className="text-sm text-status-error-800">
            {state.message}{' '}
            <button type="button" onClick={() => void load()} className="underline">
              Try again
            </button>
          </div>
        )}
        {state.status === 'loaded' && <OriginalEntryBody submission={state.submission} />}
      </section>
    </div>
  );
}
