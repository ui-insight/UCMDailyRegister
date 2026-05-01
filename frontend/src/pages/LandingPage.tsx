import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FeedbackDialog from '../components/layout/FeedbackDialog';
import { Toast, useToast } from '../components/common';
import { getBrowserFeedbackContext } from '../utils/feedback';
import { getSubmitterRole, setSubmitterRole, type SubmitterRole } from '../utils/submitterRole';

type RoleOption = {
  role: SubmitterRole;
  title: string;
  description: string;
  target: string;
};

const ROLES: RoleOption[] = [
  {
    role: 'public',
    title: 'Submitter view',
    description:
      'Send announcements, events, and news items into the newsletter pipeline.',
    target: '/submit',
  },
  {
    role: 'staff',
    title: 'Staff view',
    description:
      'Editorial workspace with dashboard, builder, style rules, and scheduling.',
    target: '/dashboard',
  },
  {
    role: 'slc',
    title: 'SLC Leadership view',
    description:
      'Private calendar of strategic and signature events for SLC members and admins.',
    target: '/slc-calendar',
  },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const { toast, showToast, dismissToast } = useToast();
  const role = getSubmitterRole();
  const feedbackContext = getBrowserFeedbackContext(role, '/');

  const handleSelect = (role: SubmitterRole, target: string) => {
    setSubmitterRole(role);
    navigate(target);
  };

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
        <p className="text-sm text-ui-silver">UCM Newsletter Builder</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ui-black">
          Choose your view
        </h1>
        <p className="mt-3 text-sm text-ui-silver">
          Pick the workspace that matches what you're doing today.
        </p>

        <ul className="mt-10 divide-y divide-gray-200 border-y border-gray-200">
          {ROLES.map((r) => (
            <li key={r.role}>
              <button
                type="button"
                onClick={() => handleSelect(r.role, r.target)}
                className="group flex w-full items-center gap-4 px-2 py-5 text-left transition hover:bg-stone-50 focus:bg-stone-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-ui-clearwater-500 rounded"
              >
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-semibold text-ui-black">
                    {r.title}
                  </h2>
                  <p className="mt-1 text-sm text-ui-silver">
                    {r.description}
                  </p>
                </div>
                <span
                  aria-hidden="true"
                  className="shrink-0 text-ui-silver transition group-hover:translate-x-0.5 group-hover:text-ui-clearwater-700"
                >
                  →
                </span>
              </button>
            </li>
          ))}
        </ul>

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
