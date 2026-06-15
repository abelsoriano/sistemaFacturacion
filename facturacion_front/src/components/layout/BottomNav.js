import React, { useMemo } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

import { bottomNavItems, isNavItemActive } from '../../navigation';
import { userHasPermissions } from '../../utils/permissions';

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}');
  } catch {
    return {};
  }
}

export default function BottomNav() {
  const location = useLocation();
  const currentUser = getCurrentUser();

  const items = useMemo(
    () => bottomNavItems.filter((item) => userHasPermissions(currentUser, item.permissions || [])),
    [currentUser],
  );

  return (
    <nav className="saas-bottom-nav" aria-label="Navegación móvil">
      {items.map((item) => {
        const Icon = item.icon;
        const active = isNavItemActive(item, location.pathname);
        return (
          <NavLink
            key={item.id}
            to={item.route}
            className={`saas-bottom-link${active ? ' is-active' : ''}${item.id === 'new-sale' ? ' is-primary' : ''}`}
            aria-label={item.label}
          >
            <Icon size={item.id === 'new-sale' ? 24 : 21} strokeWidth={1.8} />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
