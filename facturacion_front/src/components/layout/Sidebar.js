import React, { useMemo, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { MoreHorizontal, Search } from 'lucide-react';

import { isNavItemActive, navGroups } from '../../navigation';
import { userHasPermissions } from '../../utils/permissions';

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}');
  } catch {
    return {};
  }
}

export default function Sidebar() {
  const [query, setQuery] = useState('');
  const location = useLocation();
  const currentUser = getCurrentUser();

  const visibleGroups = useMemo(() => {
    const search = query.trim().toLowerCase();
    return navGroups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => {
          const canView = userHasPermissions(currentUser, item.permissions || []);
          const matches = !search || item.label.toLowerCase().includes(search);
          return canView && matches;
        }),
      }))
      .filter((group) => group.items.length > 0);
  }, [currentUser, query]);

  const initials = (
    currentUser.first_name?.[0]
    || currentUser.username?.[0]
    || currentUser.email?.[0]
    || 'U'
  ).toUpperCase();
  const displayName = currentUser.first_name || currentUser.username || 'Usuario';

  return (
    <aside className="saas-sidebar" aria-label="Navegación principal">
      <div className="saas-sidebar-search">
        <Search size={16} strokeWidth={1.7} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar"
          aria-label="Buscar módulo"
        />
      </div>

      <nav className="saas-sidebar-nav">
        {visibleGroups.map((group, index) => (
          <div className="saas-nav-group" key={group.label || `group-${index}`}>
            {group.label && <div className="saas-nav-group-label">{group.label}</div>}
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = isNavItemActive(item, `${location.pathname}${location.search}`);

              return (
                <NavLink
                  key={item.id}
                  to={item.route}
                  title={item.label}
                  className={`saas-nav-item${active ? ' is-active' : ''}`}
                >
                  <Icon size={20} strokeWidth={1.7} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="saas-sidebar-user">
        <div className="saas-user-avatar">{initials}</div>
        <div className="saas-user-meta">
          <span>{displayName}</span>
          <small>{currentUser.email || 'Sesión activa'}</small>
        </div>
        <button type="button" aria-label="Opciones de usuario" className="saas-user-menu">
          <MoreHorizontal size={17} strokeWidth={1.7} />
        </button>
      </div>
    </aside>
  );
}
