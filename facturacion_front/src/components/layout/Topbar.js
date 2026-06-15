import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Building2, ChevronDown, Search, UserCircle } from 'lucide-react';

import api from '../../services/api';
import { authService } from '../../services/api';

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}');
  } catch {
    return {};
  }
}

export default function Topbar() {
  const navigate = useNavigate();
  const currentUser = getCurrentUser();
  const dropdownRef = useRef(null);
  const [companies, setCompanies] = useState([]);
  const [activeCompany, setActiveCompany] = useState(null);
  const [isCompanyMenuOpen, setIsCompanyMenuOpen] = useState(false);
  const [isCompanyLoading, setIsCompanyLoading] = useState(() => Boolean(localStorage.getItem('token')));
  const initials = (
    currentUser.first_name?.[0]
    || currentUser.username?.[0]
    || currentUser.email?.[0]
    || 'U'
  ).toUpperCase();
  const hasMultipleCompanies = companies.length > 1;

  useEffect(() => {
    let mounted = true;

    const loadCompanyContext = async () => {
      if (!localStorage.getItem('token')) return;
      setIsCompanyLoading(true);
      try {
        const response = await api.get('/companies/active/');
        if (!mounted) return;

        const availableCompanies = response.data?.companies || [];
        const selectedCompany = response.data?.active_company || null;
        setCompanies(availableCompanies);
        setActiveCompany(selectedCompany);
        if (selectedCompany?.id) {
          localStorage.setItem('active_company_id', String(selectedCompany.id));
        } else {
          localStorage.removeItem('active_company_id');
        }
      } catch (error) {
        if (!mounted) return;
        setCompanies([]);
        setActiveCompany(null);
        localStorage.removeItem('active_company_id');
      } finally {
        if (mounted) setIsCompanyLoading(false);
      }
    };

    loadCompanyContext();
    window.addEventListener('company-context-updated', loadCompanyContext);

    return () => {
      mounted = false;
      window.removeEventListener('company-context-updated', loadCompanyContext);
    };
  }, []);

  useEffect(() => {
    const onClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsCompanyMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const switchCompany = async (company) => {
    if (!company || company.id === activeCompany?.id) {
      setIsCompanyMenuOpen(false);
      return;
    }

    try {
      const response = await api.post('/companies/switch/', { company_id: company.id });
      const selectedCompany = response.data?.active_company || company;
      localStorage.setItem('active_company_id', String(selectedCompany.id));
      setActiveCompany(selectedCompany);
      setCompanies(response.data?.companies || companies);
      setIsCompanyMenuOpen(false);
      navigate('/home', { replace: true });
      window.location.reload();
    } catch (error) {
      setIsCompanyMenuOpen(false);
    }
  };

  const logout = () => {
    authService.logout();
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('active_company_id');
    navigate('/', { replace: true });
  };

  return (
    <header className="saas-topbar">
      <button type="button" className="saas-brand" onClick={() => navigate('/home')}>
        <span className="saas-brand-mark">A</span>
        <span>Asys</span>
      </button>

      <div className="saas-company-switcher" ref={dropdownRef}>
        <button
          type="button"
          className={`saas-company-pill${hasMultipleCompanies ? ' is-clickable' : ''}`}
          onClick={() => hasMultipleCompanies && setIsCompanyMenuOpen((value) => !value)}
          disabled={!hasMultipleCompanies}
          aria-haspopup={hasMultipleCompanies ? 'listbox' : undefined}
          aria-expanded={hasMultipleCompanies ? isCompanyMenuOpen : undefined}
        >
          <span className="saas-company-dot" />
          <Building2 size={15} strokeWidth={1.8} />
          <span>{isCompanyLoading ? 'Cargando empresa...' : activeCompany?.name || (companies.length > 1 ? 'Seleccione empresa' : 'Sin empresa')}</span>
          {hasMultipleCompanies && <ChevronDown size={15} strokeWidth={1.9} />}
        </button>

        {hasMultipleCompanies && isCompanyMenuOpen && (
          <div className="saas-company-menu" role="listbox">
            {companies.map((company) => (
              <button
                key={company.id}
                type="button"
                className={`saas-company-option${company.id === activeCompany?.id ? ' is-active' : ''}`}
                onClick={() => switchCompany(company)}
                role="option"
                aria-selected={company.id === activeCompany?.id}
              >
                <span className="saas-company-avatar">
                  {(company.name || 'E').charAt(0).toUpperCase()}
                </span>
                <span className="saas-company-option-meta">
                  <strong>{company.name}</strong>
                  <small>{company.rnc ? `RNC ${company.rnc}` : company.role_label || 'Empresa'}</small>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="saas-topbar-actions">
        <button
          type="button"
          className="saas-icon-btn is-disabled"
          aria-label="Buscar - disponible proximamente"
          title="Busqueda global disponible proximamente"
          disabled
        >
          <Search size={19} strokeWidth={1.7} />
        </button>
        <button
          type="button"
          className="saas-icon-btn is-disabled"
          aria-label="Notificaciones - disponible proximamente"
          title="Notificaciones disponibles proximamente"
          disabled
        >
          <Bell size={19} strokeWidth={1.7} />
        </button>
        <button type="button" className="saas-profile-btn" onClick={() => navigate('/profile')} aria-label="Mi perfil">
          <span>{initials}</span>
          <UserCircle size={18} strokeWidth={1.7} />
        </button>
        <button type="button" className="saas-logout-btn" onClick={logout}>
          Salir
        </button>
      </div>
    </header>
  );
}
