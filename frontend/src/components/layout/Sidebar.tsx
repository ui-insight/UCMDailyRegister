import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/submit', label: 'Submit', icon: '+ ' },
  { to: '/dashboard', label: 'Dashboard', icon: '' },
  { to: '/builder', label: 'Builder', icon: '' },
  { to: '/style-rules', label: 'Style Rules', icon: '' },
  { to: '/settings', label: 'Settings', icon: '' },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <h1 className="text-lg font-bold">UCM Newsletter Builder</h1>
        <p className="text-xs text-gray-400 mt-1">University of Idaho</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `block px-4 py-2 rounded text-sm ${
                isActive
                  ? 'bg-amber-600 text-white font-medium'
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
