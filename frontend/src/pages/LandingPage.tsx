import { useNavigate } from 'react-router-dom';
import { setSubmitterRole } from '../utils/submitterRole';

type RoleCardProps = {
  title: string;
  description: string;
  actionLabel: string;
  accentClass: string;
  onSelect: () => void;
};

function RoleCard({
  title,
  description,
  actionLabel,
  accentClass,
  onSelect,
}: RoleCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`group w-full rounded-3xl border border-gray-200 bg-white p-8 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-xl ${accentClass}`}
    >
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold text-gray-900">{title}</h2>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600">
          Choose
        </span>
      </div>
      <p className="mt-4 text-sm leading-6 text-gray-600">{description}</p>
      <div className="mt-8 inline-flex items-center rounded-full bg-gray-900 px-4 py-2 text-sm font-medium text-white transition group-hover:bg-ui-gold-600">
        {actionLabel}
      </div>
    </button>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();

  const handleSelect = (role: 'public' | 'staff' | 'slc', target: string) => {
    setSubmitterRole(role);
    navigate(target);
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#f6efe1_0%,#f8fafc_45%,#eef3f7_100%)] px-6 py-12">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-[2rem] border border-white/70 bg-white/85 p-8 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur md:p-12">
          <img
            src="/ui-logo-gold-white-horizontal.png"
            alt="University of Idaho"
            className="h-12 w-auto rounded-lg bg-gray-900 px-3 py-2"
          />
          <div className="mt-8 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-ui-clearwater-700">
              UCM Newsletter Builder
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-gray-900 md:text-5xl">
              Choose how you want to enter the application.
            </h1>
            <p className="mt-5 text-base leading-7 text-gray-600 md:text-lg">
              This app supports two working modes. Submitter view is for people sending content
              into the pipeline. Staff view is for editors managing reviews, schedules, recurring
              messages and newsletter assembly.
            </p>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-3">
            <RoleCard
              title="Submitter View"
              description="Use the public-style submission experience to send announcements, events, and news items into the workflow."
              actionLabel="Open Submission Form"
              accentClass="hover:border-ui-clearwater-300"
              onSelect={() => handleSelect('public', '/submit')}
            />
            <RoleCard
              title="Staff View"
              description="Open the editorial workspace with dashboard, builder, style rules, recurring messages, and staff-only scheduling tools."
              actionLabel="Open Staff Workspace"
              accentClass="hover:border-ui-gold-300"
              onSelect={() => handleSelect('staff', '/dashboard')}
            />
            <RoleCard
              title="SLC Leadership View"
              description="Private calendar of strategic and signature events for Senior Leadership Council members and their admins. Exploration preview."
              actionLabel="Open SLC Calendar"
              accentClass="hover:border-ui-clearwater-300"
              onSelect={() => handleSelect('slc', '/slc-calendar')}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
