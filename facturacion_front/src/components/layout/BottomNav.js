import React, { useMemo, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';

import { bottomMoreItems, bottomNavItems, isNavItemActive } from '../../navigation';
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
  const navigate = useNavigate();
  const currentUser = getCurrentUser();
  const [moreOpen, setMoreOpen] = useState(false);

  const items = useMemo(
    () => bottomNavItems.filter((item) => userHasPermissions(currentUser, item.permissions || [])),
    [currentUser],
  );
  const moreItems = useMemo(
    () => bottomMoreItems.filter((item) => userHasPermissions(currentUser, item.permissions || [])),
    [currentUser],
  );
  const moreActive = moreItems.some((item) => isNavItemActive(item, location.pathname));

  const handleMoreItemClick = (route) => {
    setMoreOpen(false);
    navigate(route);
  };

  return (
    <>
      {moreOpen && (
        <div className="saas-more-backdrop" onClick={() => setMoreOpen(false)}>
          <div className="saas-more-menu" role="dialog" aria-label="Más módulos" onClick={(event) => event.stopPropagation()}>
            <div className="saas-more-handle" />
            <header>
              <strong>Más módulos</strong>
              <button type="button" onClick={() => setMoreOpen(false)} aria-label="Cerrar menú">
                ×
              </button>
            </header>
            {moreItems.length === 0 ? (
              <div className="saas-more-empty">No hay más módulos disponibles.</div>
            ) : (
              <div className="saas-more-grid">
                {moreItems.map((item) => {
                  const Icon = item.icon;
                  const active = isNavItemActive(item, location.pathname);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`saas-more-item${active ? ' is-active' : ''}`}
                      onClick={() => handleMoreItemClick(item.route)}
                    >
                      <Icon size={18} strokeWidth={1.8} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      <nav className="saas-bottom-nav" aria-label="Navegación móvil">
        {items.map((item) => {
          const Icon = item.icon;
          const active = item.id === 'more' ? moreActive || moreOpen : isNavItemActive(item, location.pathname);

          if (item.id === 'more') {
            return (
              <button
                key={item.id}
                type="button"
                className={`saas-bottom-link saas-bottom-button${active ? ' is-active' : ''}`}
                aria-label="Más módulos"
                aria-expanded={moreOpen}
                onClick={() => setMoreOpen((open) => !open)}
              >
                <Icon size={21} strokeWidth={1.8} />
                <span>{item.label}</span>
              </button>
            );
          }

          return (
            <NavLink
              key={item.id}
              to={item.route}
              className={`saas-bottom-link${active ? ' is-active' : ''}${item.id === 'new-sale' ? ' is-primary' : ''}`}
              aria-label={item.label}
              onClick={() => setMoreOpen(false)}
            >
              <Icon size={item.id === 'new-sale' ? 24 : 21} strokeWidth={1.8} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}
