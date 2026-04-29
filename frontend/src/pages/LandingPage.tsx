import { useNavigate } from 'react-router-dom';
import { setSubmitterRole, type SubmitterRole } from '../utils/submitterRole';

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

  const handleSelect = (role: SubmitterRole, target: string) => {
    setSubmitterRole(role);
    navigate(target);
  };

  return (
    <div className="min-h-screen bg-white">
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
      </main>
    </div>
  );
}
