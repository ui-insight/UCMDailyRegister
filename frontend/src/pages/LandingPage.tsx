import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { SSO_LOGIN_URL } from '../api/auth';
import { getValidDates } from '../api/schedule';
import { useAuthMode, useIdentity } from '../auth/useAuth';
import MicrosoftMark from '../components/common/MicrosoftMark';
import { addDaysISO, formatAPDate, todayISO } from '../utils/date';
import { homeForRole, setSubmitterRole } from '../utils/submitterRole';

type NewsletterKey = 'tdr' | 'myui';

const NEWSLETTERS: { key: NewsletterKey; name: string; audience: string }[] = [
  { key: 'tdr', name: 'The Daily Register', audience: 'faculty and staff' },
  { key: 'myui', name: 'My UI', audience: 'students' },
];

// Far enough ahead to reach past winter break and summer pauses.
const NEXT_ISSUE_LOOKAHEAD_DAYS = 120;

const PRIMARY_BUTTON =
  'inline-flex w-full items-center justify-center gap-2.5 rounded-lg bg-ui-gold-500 px-6 py-3 '
  + 'text-sm font-semibold text-ui-black shadow-sm transition hover:bg-ui-gold-400 '
  + 'focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 '
  + 'focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-70 sm:w-auto';

const TEXT_LINK =
  'font-medium text-ui-clearwater-700 underline-offset-2 hover:underline '
  + 'focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500';

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

/**
 * The front door: one University sign-in for everyone (ADR-002).
 *
 * There is no choice of views. After sign-in the backend's role decides where
 * a person lands: staff on the dashboard, everyone else on the submission
 * form. A visitor who is already signed in goes straight there.
 *
 * Header-mode deployments (local development) have no sign-in, so they get
 * plain links to the two workspaces instead. Those links appear only after
 * the backend says so: if the check fails, the page offers a retry rather
 * than an anonymous form the backend would refuse.
 */
export default function LandingPage() {
  const navigate = useNavigate();
  const { mode, retry } = useAuthMode();
  const identity = useIdentity();
  const nextIssues = useNextIssues();
  const [redirecting, setRedirecting] = useState(false);

  if (mode === 'sso' && identity) {
    return <Navigate to={homeForRole(identity.role)} replace />;
  }

  const handleSignIn = () => {
    setRedirecting(true);
    window.location.assign(SSO_LOGIN_URL);
  };

  const openWithoutSignIn = (path: '/submit' | '/dashboard') => {
    setSubmitterRole(path === '/dashboard' ? 'staff' : 'public');
    navigate(path);
  };

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="bg-gray-900">
        <div className="mx-auto max-w-3xl px-6 py-4">
          <img
            src="/ui-logo-gold-white-horizontal.png"
            alt="University of Idaho"
            className="h-8 w-auto"
          />
        </div>
      </header>

      <main className="mx-auto w-full max-w-xl flex-1 px-6 py-16 sm:py-24">
        <p className="text-sm text-ui-silver">University Communications and Marketing</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ui-black sm:text-4xl">
          UCM Newsletter Submissions
        </h1>
        <p className="mt-4 text-base leading-relaxed text-gray-600">
          Send announcements, events, and news to{' '}
          {NEWSLETTERS.map((newsletter, index) => (
            <span key={newsletter.key}>
              {index > 0 && ' and '}
              <span className="font-medium text-ui-black">{newsletter.name}</span>
              {' '}({newsletter.audience})
            </span>
          ))}
          . UCM editors review every item before it runs.
        </p>

        {mode === 'header' ? (
          <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
            <button
              type="button"
              onClick={() => openWithoutSignIn('/submit')}
              className={PRIMARY_BUTTON}
            >
              Submit an item
            </button>
            <button
              type="button"
              onClick={() => openWithoutSignIn('/dashboard')}
              className={`text-sm ${TEXT_LINK}`}
            >
              Open the staff workspace
            </button>
          </div>
        ) : mode === 'error' ? (
          <div className="mt-10" role="alert">
            <p className="text-sm text-gray-600">
              Sign-in isn't available right now. Check your connection, then try again.
            </p>
            <button type="button" onClick={retry} className={`mt-4 ${PRIMARY_BUTTON}`}>
              Try again
            </button>
          </div>
        ) : (
          <div className="mt-10">
            <button
              type="button"
              onClick={handleSignIn}
              disabled={mode === null || redirecting}
              className={PRIMARY_BUTTON}
            >
              <MicrosoftMark />
              {redirecting ? 'Redirecting to Microsoft…' : 'Sign in with your University account'}
            </button>
            <p className="mt-3 text-xs leading-relaxed text-ui-silver">
              Your password is entered on the University sign-in page, never here.
            </p>
          </div>
        )}

        {(nextIssues.tdr || nextIssues.myui) && (
          <dl className="mt-14 grid gap-4 border-t border-gray-200 pt-6 text-sm sm:grid-cols-2">
            {NEWSLETTERS.map((newsletter) =>
              nextIssues[newsletter.key] ? (
                <div key={newsletter.key} data-testid={`next-issue-${newsletter.key}`}>
                  <dt className="text-ui-silver">Next {newsletter.name}</dt>
                  <dd className="mt-0.5 font-medium text-ui-black">
                    {formatAPDate(nextIssues[newsletter.key]!)}
                  </dd>
                </div>
              ) : null,
            )}
          </dl>
        )}
      </main>
    </div>
  );
}
