import { NavLink, Outlet } from 'react-router-dom';
import './Layout.css';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/companies', label: 'Companies' },
  { to: '/upload', label: 'Upload & Extract' },
  { to: '/analytics', label: 'Analytics' },
];

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>Seben CRM</strong>
            <small>Customer Intelligence</small>
          </div>
        </div>
        <nav>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="phase-badge">Phase 1 Prototype</span>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
