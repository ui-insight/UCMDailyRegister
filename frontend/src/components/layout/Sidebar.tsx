import { NavLink } from 'react-router-dom';
import { getSubmitterRole } from '../../utils/submitterRole';

type NavItem = {
  to: string;
  label: string;
  icon: string;
  roles: ('public' | 'staff' | 'slc')[];
};

const navItems: NavItem[] = [
  { to: '/submit', label: 'Submit', icon: '+ ', roles: ['public', 'staff', 'slc'] },
  { to: '/dashboard', label: 'Dashboard', icon: '', roles: ['staff'] },
  { to: '/builder', label: 'Builder', icon: '', roles: ['staff'] },
  { to: '/recurring-messages', label: 'Recurring', icon: '', roles: ['staff'] },
  { to: '/slc-calendar', label: 'SLC Calendar', icon: '', roles: ['staff', 'slc'] },
  { to: '/submit-slc-event', label: 'Submit SLC Event', icon: '+ ', roles: ['staff', 'slc'] },
  { to: '/style-rules', label: 'Style Rules', icon: '', roles: ['staff'] },
  { to: '/data-governance', label: 'Data Governance', icon: '', roles: ['staff'] },
  { to: '/settings', label: 'Settings', icon: '', roles: ['staff'] },
];

const ROLE_LABEL: Record<'public' | 'staff' | 'slc', string> = {
  public: 'Submitter View',
  staff: 'Staff View',
  slc: 'SLC Leadership View',
};

export default function Sidebar() {
  const role = getSubmitterRole();
  const filteredNavItems = navItems.filter((item) => item.roles.includes(role));

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <img
          src="/ui-logo-gold-white-horizontal.png"
          alt="University of Idaho"
          className="h-10 w-auto mb-2"
        />
        <p className="text-xs text-gray-400">UCM Newsletter Builder</p>
        <div className="mt-4 rounded-lg border border-gray-700 bg-gray-800/80 px-3 py-2">
          <p className="text-[11px] uppercase tracking-wide text-gray-500">Current Mode</p>
          <p className="mt-1 text-sm font-medium text-white">
            {ROLE_LABEL[role]}
          </p>
          <NavLink
            to="/"
            className="mt-2 inline-flex text-xs font-medium text-ui-gold-300 hover:text-ui-gold-200"
          >
            Switch mode
          </NavLink>
        </div>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {filteredNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `block px-4 py-2 rounded text-sm ${
                isActive
                  ? 'bg-ui-gold-500 text-ui-black font-medium'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            {item.icon}{item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
