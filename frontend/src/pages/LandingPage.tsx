import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SSO_LOGOUT_URL } from '../api/auth';
import { getValidDates } from '../api/schedule';
import { clearToken } from '../auth/tokenStore';
import { useIdentity, useSsoEnabled } from '../auth/useAuth';
import FeedbackDialog from '../components/layout/FeedbackDialog';
import { loginUrlFor } from '../auth/loginUrl';
import { Toast, useToast } from '../components/common';
import { addDaysISO, formatAPDate, todayISO } from '../utils/date';
import { getBrowserFeedbackContext } from '../utils/feedback';
import {
  getSubmitterRole,
  roleMayOpen,
  setSubmitterRole,
} from '../utils/submitterRole';

type NewsletterKey = 'tdr' | 'myui';

const NEWSLETTERS: { key: NewsletterKey; name: string; audience: string }[] = [
  {
    key: 'tdr',
    name: 'The Daily Register',
    audience: 'For faculty and staff.',
  },
  {
    key: 'myui',
    name: 'My UI',
    audience: 'For students.',
  },
];

// Far enough ahead to reach past winter break and summer pauses.
const NEXT_ISSUE_LOOKAHEAD_DAYS = 120;

/** The first publication date after today for each newsletter, from the public schedule. */
function useNextIssues(): Partial<Record<NewsletterKey, string>> {
  const [nextIssues, setNextIssues] = useState<Partial<Record<NewsletterKey, string>>>({});

  useEffect(() => {
    let cancelled = false;
    const today = todayISO();
    getValidDates(today, addDaysISO(NEXT_ISSUE_LOOKAHEAD_DAYS))
      .then(({ dates }) => {
        if (cancelled) return;
        const found: Partial<Record<NewsletterKey, string>> = {};
        for (const { date, newsletters } of dates) {
          if (date <= today) continue;
          for (const key of ['tdr', 'myui'] as const) {
            if (!found[key] && newsletters.includes(key)) found[key] = date;
          }
        }
        setNextIssues(found);
      })
      .catch(() => {
        // The dates are a convenience; the page works without them.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return nextIssues;
}

export default function LandingPage() {
  const navigate = useNavigate();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const { toast, showToast, dismissToast } = useToast();
  const ssoEnabled = useSsoEnabled();
  const identity = useIdentity();
  const nextIssues = useNextIssues();
  const feedbackContext = getBrowserFeedbackContext(getSubmitterRole(), '/');

  const handleSubmit = () => {
    // Submitting is open to everyone under every deployment.
    if (!identity) setSubmitterRole('public');
    navigate('/submit');
  };

  const handleStaff = () => {
    if (ssoEnabled !== true) {
      setSubmitterRole('staff');
      navigate('/dashboard');
      return;
    }
    // SSO deployment: a signed-in staff member goes straight in; anyone else
    // goes to the sign-in page, and the backend decides the role on return.
    if (identity && roleMayOpen(identity.role, '/dashboard')) {
      setSubmitterRole(identity.role);
      navigate('/dashboard');
      return;
    }
    navigate(loginUrlFor('/dashboard'));
  };

  const handleSignOut = () => {
    clearToken();
    window.location.assign(SSO_LOGOUT_URL);
  };

  const signedInStaff = ssoEnabled === true && identity?.role === 'staff' ? identity : null;

  return (
    <div className="min-h-screen bg-white">
      <Toast toast={toast} onDismiss={dismissToast} />
      <FeedbackDialog
        open={feedbackOpen}
        context={feedbackContext}
        onClose={() => setFeedbackOpen(false)}
        onSubmitted={() => showToast('Feedback submitted')}
      />
      <header className="bg-gray-900">
        <div className="mx-auto max-w-3xl px-6 py-4">
          <img
            src="/ui-logo-gold-white-horizontal.png"
            alt="University of Idaho"
            className="h-8 w-auto"
          />
        </div>
      </header>

      <main className="mx-auto max-w-xl px-6 py-16">
        <p className="text-sm text-ui-silver">UCM News</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ui-black">
          Submit to The Daily Register and My UI
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-gray-600">
          University Communications and Marketing publishes two campus newsletters. Send
          announcements, events, and news here. UCM editors review every item before it runs.
        </p>

        <ul className="mt-10 divide-y divide-gray-200 border-y border-gray-200">
          {NEWSLETTERS.map((newsletter) => (
            <li
              key={newsletter.key}
              className="flex flex-col gap-1 px-2 py-5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6"
            >
              <div>
                <h2 className="text-base font-semibold text-ui-black">{newsletter.name}</h2>
                <p className="mt-1 text-sm text-ui-silver">{newsletter.audience}</p>
              </div>
              {nextIssues[newsletter.key] && (
                <p
                  className="shrink-0 text-sm text-gray-600"
                  data-testid={`next-issue-${newsletter.key}`}
                >
                  Next issue{' '}
                  <span className="font-medium text-ui-black">
                    {formatAPDate(nextIssues[newsletter.key]!)}
                  </span>
                </p>
              )}
            </li>
          ))}
        </ul>

        <button
          type="button"
          onClick={handleSubmit}
          className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-ui-gold-500 px-4 py-3 text-sm font-semibold text-ui-black shadow-sm transition hover:bg-ui-gold-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 focus-visible:ring-offset-2 sm:w-auto sm:px-6"
        >
          Submit an item
          <span aria-hidden="true">→</span>
        </button>
        <p className="mt-3 text-xs text-ui-silver">No sign-in needed.</p>

        <section className="mt-14 border-t border-gray-200 pt-6" aria-labelledby="staff-heading">
          <h2 id="staff-heading" className="text-sm font-semibold text-ui-black">
            UCM staff
          </h2>
          {signedInStaff ? (
            <p className="mt-2 text-sm text-ui-silver" data-testid="sign-in-status">
              Signed in as <span className="font-medium text-ui-black">{signedInStaff.name}</span>
              {' · '}
              <button
                type="button"
                onClick={handleStaff}
                className="font-medium text-ui-clearwater-700 underline-offset-2 hover:underline"
              >
                Go to dashboard
              </button>
              {' · '}
              <button
                type="button"
                onClick={handleSignOut}
                className="font-medium text-ui-clearwater-700 underline-offset-2 hover:underline"
              >
                Sign out
              </button>
            </p>
          ) : (
            <p className="mt-2 text-sm text-ui-silver">
              Editors and newsletter staff work in the editorial workspace.{' '}
              <button
                type="button"
                onClick={handleStaff}
                className="font-medium text-ui-clearwater-700 underline-offset-2 hover:underline"
              >
                {ssoEnabled === true ? 'Staff sign in' : 'Open the staff workspace'}
              </button>
            </p>
          )}
        </section>

        <button
          type="button"
          onClick={() => setFeedbackOpen(true)}
          className="mt-8 inline-flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm font-medium text-ui-silver transition hover:border-ui-gold-400 hover:text-ui-black focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500"
          title="Open the in-app feedback form"
        >
          <span
            aria-hidden="true"
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ui-gold-500 text-[11px] font-semibold text-ui-black"
          >
            ?
          </span>
          Report bug or idea
        </button>
      </main>
    </div>
  );
}
