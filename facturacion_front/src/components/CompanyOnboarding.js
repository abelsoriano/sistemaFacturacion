import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Building2, CheckCircle2, Mail, MapPin, Phone, Save } from 'lucide-react';
import api from '../services/api';
import { normalizeRncInput, validatePhone, validateRnc } from '../utils/validators';
import '../css/CompanyPage.css';

const initialCompany = {
  name: '',
  legal_name: '',
  rnc: '',
  email: '',
  phone: '',
  address: '',
};

export default function CompanyOnboarding() {
  const [formData, setFormData] = useState(initialCompany);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const extractError = (err) => {
    const data = err.response?.data;
    if (!data) return 'No pudimos crear la empresa. Intenta nuevamente.';
    if (typeof data === 'string') return data;
    if (data.detail) return data.detail;
    const firstKey = Object.keys(data)[0];
    const firstValue = firstKey ? data[firstKey] : null;
    if (Array.isArray(firstValue)) return firstValue[0];
    if (typeof firstValue === 'string') return firstValue;
    return 'Revisa los datos de la empresa.';
  };

  const handleChange = (event) => {
    const value = event.target.name === 'rnc'
      ? normalizeRncInput(event.target.value)
      : event.target.value;
    setFormData((current) => ({
      ...current,
      [event.target.name]: value,
    }));
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (!formData.name.trim()) {
      setError('El nombre comercial es obligatorio.');
      return;
    }
    const rncError = validateRnc(formData.rnc, { label: 'RNC de la empresa' });
    if (rncError) {
      setError(rncError);
      return;
    }
    const phoneError = validatePhone(formData.phone, { label: 'Telefono de la empresa' });
    if (phoneError) {
      setError(phoneError);
      return;
    }

    setSaving(true);
    try {
      const response = await api.post('/companies/setup-first/', formData);
      const activeCompany = response.data?.active_company;
      if (activeCompany?.id) {
        localStorage.setItem('active_company_id', activeCompany.id);
        window.dispatchEvent(new CustomEvent('company:changed', { detail: activeCompany }));
      }
      navigate('/home', { replace: true });
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="company-page company-onboarding-page">
      <section className="company-hero">
        <div>
          <span className="company-kicker">Primer acceso</span>
          <h1>Configura tu primera empresa</h1>
          <p>
            Necesitamos una empresa activa para aislar datos, permisos y flujos
            fiscales antes de abrir el dashboard.
          </p>
        </div>
        <span className="company-state inactive">Pendiente</span>
      </section>

      <section className="company-grid onboarding-grid">
        <article className="company-card">
          <header>
            <span className="company-card-icon">
              <Building2 size={20} />
            </span>
            <div>
              <h2>Datos mínimos</h2>
              <p>Crearás la empresa y quedarás asignado como owner inicial.</p>
            </div>
          </header>

          {error && (
            <div className="company-form-error" role="alert">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}

          <form className="company-form onboarding-form" onSubmit={handleSubmit}>
            <div className="company-form-grid">
              <label>
                <span>Nombre comercial *</span>
                <input
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Ej. FacturApp"
                  required
                />
              </label>
              <label>
                <span>Razón social</span>
                <input
                  name="legal_name"
                  value={formData.legal_name}
                  onChange={handleChange}
                  placeholder="Ej. FacturApp SRL"
                />
              </label>
              <label>
                <span>RNC</span>
                <input
                  name="rnc"
                  value={formData.rnc}
                  onChange={handleChange}
                  placeholder="RNC de la empresa"
                  inputMode="numeric"
                  maxLength={11}
                />
                <small>Solo numeros, 9 u 11 digitos.</small>
              </label>
              <label>
                <span>Email</span>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="empresa@email.com"
                />
              </label>
              <label>
                <span>Teléfono</span>
                <input
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="+1 (809) 000-0000"
                  maxLength={20}
                />
                <small>Puede incluir espacios, guiones, parentesis o +.</small>
              </label>
              <label className="company-form-wide">
                <span>Dirección</span>
                <textarea
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  placeholder="Dirección fiscal o comercial"
                  rows="3"
                />
              </label>
            </div>
            <div className="company-form-actions">
              <button type="submit" disabled={saving}>
                <Save size={16} />
                {saving ? 'Creando empresa...' : 'Crear empresa y continuar'}
              </button>
            </div>
          </form>
        </article>

        <aside className="company-card onboarding-aside">
          <header>
            <span className="company-card-icon">
              <CheckCircle2 size={20} />
            </span>
            <div>
              <h2>Qué ocurre después</h2>
              <p>El sistema seleccionará la empresa y abrirá el dashboard.</p>
            </div>
          </header>
          <dl className="company-facts onboarding-facts">
            <div>
              <dt><Building2 size={13} /> Empresa</dt>
              <dd>Tenant activo</dd>
            </div>
            <div>
              <dt><CheckCircle2 size={13} /> Rol</dt>
              <dd>Owner</dd>
            </div>
            <div>
              <dt><Mail size={13} /> Datos</dt>
              <dd>Aislados por empresa</dd>
            </div>
            <div>
              <dt><MapPin size={13} /> Fiscal</dt>
              <dd>Configurable luego</dd>
            </div>
            <div className="company-form-wide">
              <dt><Phone size={13} /> Siguiente paso</dt>
              <dd>Completar onboarding fiscal en Empresa</dd>
            </div>
          </dl>
        </aside>
      </section>
    </div>
  );
}
