import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ArrowRight,
  AlertTriangle,
  BadgeCheck,
  Building2,
  CheckCircle2,
  CircleAlert,
  CircleDashed,
  Edit3,
  FileKey2,
  IdCard,
  ListChecks,
  Mail,
  Phone,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  X,
} from 'lucide-react';

import api from '../services/api';
import { normalizeRncInput, validatePhone, validateRnc } from '../utils/validators';
import '../css/CompanyPage.css';

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

const certificateStatusMeta = {
  missing: {
    label: 'Faltante',
    tone: 'danger',
    alert: 'Certificado DGII faltante. Configure el certificado del emisor antes de operar e-CF reales.',
    action: 'Configure el certificado DGII',
  },
  active: {
    label: 'Activo',
    tone: 'success',
    alert: null,
    action: 'Certificado válido',
  },
  expiring_soon: {
    label: 'Por vencer',
    tone: 'warning',
    alert: 'Certificado DGII por vencer. Planifique renovación antes de 30 días.',
    action: 'Certificado próximo a vencer',
  },
  expired: {
    label: 'Vencido',
    tone: 'danger',
    alert: 'Certificado DGII vencido. No debe firmar documentos fiscales reales.',
    action: 'Renueve el certificado',
  },
  invalid: {
    label: 'Inválido',
    tone: 'danger',
    alert: 'Certificado DGII inválido o ilegible. Revise archivo, formato y contraseña.',
    action: 'Revise archivo o contraseña del certificado',
  },
};

const certificateRncMatchMeta = {
  unknown: {
    label: 'Desconocido',
    tone: 'warning',
    alert: null,
  },
  matched: {
    label: 'Coincide',
    tone: 'success',
    alert: null,
  },
  mismatch: {
    label: 'No coincide',
    tone: 'danger',
    alert: 'El RNC detectado en el certificado no coincide con el RNC del emisor.',
  },
  not_found: {
    label: 'No encontrado',
    tone: 'warning',
    alert: null,
  },
};

const environmentLabels = {
  testing: 'Pruebas',
  certification: 'Certificación',
  production: 'Producción',
};

const membershipRoleOptions = [
  { value: 'owner', label: 'Owner' },
  { value: 'admin', label: 'Admin' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'cashier', label: 'Cajero' },
  { value: 'accountant', label: 'Contador' },
  { value: 'readonly', label: 'Solo lectura' },
];

function formatDate(value, withTime = false) {
  if (!value) return 'No disponible';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No disponible';
  return date.toLocaleString('es-DO', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  });
}

function compactFingerprint(value) {
  if (!value) return 'No disponible';
  if (value.length <= 20) return value;
  return `${value.slice(0, 12)}...${value.slice(-8)}`;
}

export default function CompanyPage({ initialTab = 'summary' }) {
  const [searchParams] = useSearchParams();
  const [company, setCompany] = useState(null);
  const [issuers, setIssuers] = useState([]);
  const [sequences, setSequences] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [modalError, setModalError] = useState('');
  const [modal, setModal] = useState(null);
  const [activeTab, setActiveTab] = useState(initialTab);
  const companyRef = React.useRef(null);
  const issuerRef = React.useRef(null);
  const sequenceRef = React.useRef(null);

  const loadCompanyPage = React.useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [companyResponse, issuersResponse, sequencesResponse, membersResponse] = await Promise.all([
        api.get('/companies/active/'),
        api.get('/ecf/issuers/'),
        api.get('/ecf/sequences/'),
        api.get('/companies/members/').catch((err) => ({ error: err, data: [] })),
      ]);
      const normalizedIssuers = normalizeList(issuersResponse.data);
      const issuersWithCertificates = await Promise.all(
        normalizedIssuers.map(async (issuer) => {
          try {
            const response = await api.get(`/ecf/issuers/${issuer.id}/certificates/`);
            return { ...issuer, certificates: normalizeList(response.data) };
          } catch (_err) {
            return { ...issuer, certificates: [] };
          }
        })
      );

      setCompany(companyResponse.data?.active_company || null);
      setIssuers(issuersWithCertificates);
      setSequences(normalizeList(sequencesResponse.data));
      setMembers(normalizeList(membersResponse.data));
    } catch (err) {
      setError(err.response?.data?.detail || 'No fue posible cargar la información de empresa.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const requestedTab = searchParams.get('tab');
    if (['summary', 'fiscal', 'sequences', 'members'].includes(requestedTab)) {
      setActiveTab(requestedTab);
    } else if (['summary', 'fiscal', 'sequences', 'members'].includes(initialTab)) {
      setActiveTab(initialTab);
    }
  }, [initialTab, searchParams]);

  useEffect(() => {
    let mounted = true;
    loadCompanyPage().finally(() => {
      if (!mounted) return;
    });
    return () => {
      mounted = false;
    };
  }, [loadCompanyPage]);

  const alerts = useMemo(() => (
    issuers
      .flatMap((issuer) => {
        const status = issuer.certificate_status || 'missing';
        const meta = certificateStatusMeta[status] || certificateStatusMeta.invalid;
        const rncMatchStatus = issuer.certificate_rnc_match_status || 'unknown';
        const rncMatchMeta = certificateRncMatchMeta[rncMatchStatus] || certificateRncMatchMeta.unknown;
        const issuerName = issuer.business_name || issuer.trade_name || 'Emisor fiscal';
        return [
          meta.alert
            ? {
                id: `${issuer.id}-certificate-status`,
                issuerName,
                message: meta.alert,
                tone: meta.tone,
              }
            : null,
          rncMatchMeta.alert
            ? {
                id: `${issuer.id}-certificate-rnc`,
                issuerName,
                message: rncMatchMeta.alert,
                tone: rncMatchMeta.tone,
              }
            : null,
        ];
      })
      .filter(Boolean)
  ), [issuers]);

  const scrollTo = (ref, tab = null) => {
    if (tab) {
      setActiveTab(tab);
    }
    setTimeout(() => {
      ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
  };

  const openPlaceholder = (title, message) => {
    setModalError('');
    setModal({
      title,
      message,
      type: 'placeholder',
    });
  };

  const checklistActions = {
    company_data: () => scrollTo(companyRef, 'summary'),
    company_rnc: () => scrollTo(companyRef, 'summary'),
    issuer: () => openCreateIssuer(),
    certificate: () => openUploadCertificate(issuers.find((issuer) => issuer.is_active) || issuers[0]),
    sequence_31: () => openCreateSequence('31'),
    sequence_32: () => openCreateSequence('32'),
    sequence_34: () => openCreateSequence('34'),
  };

  const checklist = useMemo(() => buildFiscalChecklist(company, issuers, sequences), [company, issuers, sequences]);
  const canManageCompany = ['owner', 'admin'].includes(company?.role);

  const notifyCompanyContextChanged = () => {
    window.dispatchEvent(new CustomEvent('company-context-updated'));
  };

  const openEditCompany = () => {
    setModalError('');
    setModal({
      title: 'Editar empresa activa',
      type: 'company-edit',
      company,
    });
  };

  const openCreateCompany = () => {
    setModalError('');
    setModal({
      title: 'Crear empresa',
      type: 'company-create',
      company: {
        name: '',
        legal_name: '',
        rnc: '',
        email: '',
        phone: '',
        address: '',
        primary_color: '',
      },
    });
  };

  const openAddMember = () => {
    setModalError('');
    setModal({
      title: 'Agregar miembro',
      type: 'member-add',
      member: { email: '', role: 'cashier' },
    });
  };

  const openEditMember = (member) => {
    setModalError('');
    setModal({
      title: 'Editar miembro',
      type: 'member-edit',
      member,
    });
  };

  const openCreateIssuer = () => {
    setModalError('');
    setActiveTab('fiscal');
    setModal({
      title: 'Configurar emisor fiscal',
      type: 'issuer-create',
      issuer: {
        business_name: company?.legal_name || company?.name || '',
        trade_name: company?.name || '',
        rnc: company?.rnc || '',
        environment: 'testing',
        is_active: issuers.length === 0,
      },
    });
  };

  const openCreateSequence = (ecfType = '31') => {
    setModalError('');
    setActiveTab('sequences');
    setModal({
      title: `Configurar E${ecfType}`,
      type: 'sequence-create',
      sequence: {
        ecf_type: ecfType,
        issuer: issuers.find((issuer) => issuer.is_active)?.id || issuers[0]?.id || '',
        start_number: 1,
        end_number: 100,
        next_number: 1,
        expiration_date: '',
        is_active: true,
      },
    });
  };

  function openUploadCertificate(issuer) {
    setModalError('');
    setActiveTab('fiscal');
    if (!issuer) {
      openPlaceholder(
        'Configurar certificado DGII',
        'Primero debes crear un emisor fiscal para poder cargar su certificado DGII.',
      );
      return;
    }
    setModal({
      title: 'Cargar certificado DGII',
      type: 'certificate-upload',
      issuer,
    });
  }

  const saveCompany = async (form) => {
    if (!String(form.name || '').trim()) {
      setError('El nombre comercial es obligatorio.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await api.patch(`/companies/${company.id}/`, form);
      setModal(null);
      await loadCompanyPage();
      notifyCompanyContextChanged();
    } catch (err) {
      setError(err.response?.data?.detail || firstApiError(err.response?.data) || 'No fue posible guardar la empresa.');
    } finally {
      setSaving(false);
    }
  };

  const createCompany = async (form) => {
    if (!String(form.name || '').trim()) {
      setError('El nombre comercial es obligatorio.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const response = await api.post('/companies/', form);
      if (response.data?.id) {
        await api.post('/companies/switch/', { company_id: response.data.id });
        localStorage.setItem('active_company_id', String(response.data.id));
      }
      setModal(null);
      await loadCompanyPage();
      notifyCompanyContextChanged();
    } catch (err) {
      setError(err.response?.data?.detail || firstApiError(err.response?.data) || 'No fue posible crear la empresa.');
    } finally {
      setSaving(false);
    }
  };

  const addMember = async (form) => {
    setSaving(true);
    setModalError('');
    try {
      await api.post('/companies/members/', form);
      setModal(null);
      await loadCompanyPage();
    } catch (err) {
      setModalError(err.response?.data?.detail || firstApiError(err.response?.data) || 'No fue posible agregar el miembro.');
    } finally {
      setSaving(false);
    }
  };

  const updateMember = async (memberId, form) => {
    setSaving(true);
    setModalError('');
    try {
      await api.patch(`/companies/members/${memberId}/`, form);
      setModal(null);
      await loadCompanyPage();
      notifyCompanyContextChanged();
    } catch (err) {
      setModalError(err.response?.data?.detail || firstApiError(err.response?.data) || 'No fue posible actualizar el miembro.');
    } finally {
      setSaving(false);
    }
  };

  const createIssuer = async (form) => {
    setSaving(true);
    setModalError('');
    try {
      await api.post('/ecf/issuers/', {
        business_name: form.business_name,
        trade_name: form.trade_name || company?.name || '',
        rnc: form.rnc,
        address: company?.address || 'Pendiente de configurar',
        phone: company?.phone || '',
        email: company?.email || '',
        environment: form.environment,
        default_ecf_type: '32',
        auto_ecf_rules_enabled: true,
        is_active: form.is_active,
      });
      setModal(null);
      await loadCompanyPage();
      setActiveTab('fiscal');
    } catch (err) {
      setModalError(err.response?.data?.detail || firstApiError(err.response?.data) || 'No fue posible crear el emisor fiscal.');
    } finally {
      setSaving(false);
    }
  };

  const createSequence = async (form) => {
    setSaving(true);
    setModalError('');
    try {
      await api.post('/ecf/sequences/', {
        issuer: form.issuer,
        ecf_type: form.ecf_type,
        start_number: form.start_number,
        end_number: form.end_number,
        next_number: form.next_number || form.start_number,
        expiration_date: form.expiration_date || null,
        is_active: form.is_active,
      });
      setModal(null);
      await loadCompanyPage();
      setActiveTab('sequences');
    } catch (err) {
      setModalError(err.response?.data?.detail || firstApiError(err.response?.data) || 'No fue posible crear la secuencia e-CF.');
    } finally {
      setSaving(false);
    }
  };

  const uploadCertificate = async (issuerId, form) => {
    setSaving(true);
    setModalError('');
    try {
      const payload = new FormData();
      payload.append('certificate', form.certificate);
      payload.append('password', form.password || '');
      await api.post(`/ecf/issuers/${issuerId}/certificate/`, payload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setModal(null);
      await loadCompanyPage();
      setActiveTab('fiscal');
    } catch (err) {
      setModalError(err.response?.data?.detail || firstApiError(err.response?.data) || 'No fue posible cargar el certificado DGII.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="company-page">
      <header className="company-hero">
        <div>
          <span className="company-kicker">Empresa activa</span>
          <h1>{company?.name || 'Empresa'}</h1>
          <p>Información corporativa, emisores fiscales y estado operativo de certificados DGII.</p>
        </div>
        <div className="company-hero-actions">
          {canManageCompany && (
            <>
              <button type="button" onClick={openEditCompany}>
                <Edit3 size={15} strokeWidth={1.8} />
                Editar empresa
              </button>
              <button type="button" onClick={openCreateCompany}>
                <Plus size={15} strokeWidth={1.8} />
                Crear empresa
              </button>
            </>
          )}
          <span className={`company-state ${company?.is_active ? 'active' : 'inactive'}`}>
            {company?.is_active ? 'Activa' : 'Inactiva'}
          </span>
        </div>
      </header>

      {error && (
        <div className="company-inline-alert danger">
          <CircleAlert size={18} strokeWidth={1.8} />
          {error}
        </div>
      )}

      {loading ? (
        <div className="company-loading">
          <RefreshCw size={18} strokeWidth={1.8} />
          Cargando información fiscal...
        </div>
      ) : (
        <>
          <CompanyTabs activeTab={activeTab} onChange={setActiveTab} />

          {activeTab === 'summary' && (
            <>
              <section className="company-grid">
                <CompanyInfoCard company={company} refProp={companyRef} />
                <IssuerSummary issuers={issuers} sequences={sequences} />
              </section>

              <FiscalOnboardingChecklist items={checklist} actions={checklistActions} />

              <NextStepsCard />
            </>
          )}

          {activeTab === 'fiscal' && (
            <IssuerSection
              issuers={issuers}
              alerts={alerts}
              canManage={canManageCompany}
              refProp={issuerRef}
              onCreateIssuer={openCreateIssuer}
              onViewSequences={() => scrollTo(sequenceRef, 'sequences')}
              onViewDetails={(issuer) => {
                setModalError('');
                setModal({
                  title: issuer.business_name || issuer.trade_name || 'Emisor fiscal',
                  type: 'issuer',
                  issuer,
                });
              }}
              onConfigureCertificate={openUploadCertificate}
            />
          )}

          {activeTab === 'sequences' && (
            <SequenceSection
              sequences={sequences}
              canManage={canManageCompany}
              refProp={sequenceRef}
              onCreateSequence={openCreateSequence}
            />
          )}

          {activeTab === 'members' && (
            <CompanyMembersSection
              members={members}
              canManage={canManageCompany}
              onAddMember={openAddMember}
              onEditMember={openEditMember}
              onToggleMember={(member) => updateMember(member.id, { is_active: !member.is_active })}
            />
          )}
        </>
      )}

      {modal && (
        <CompanyInfoModal
          modal={modal}
          saving={saving}
          onClose={() => setModal(null)}
          onSaveCompany={saveCompany}
          onCreateCompany={createCompany}
          onAddMember={addMember}
          onUpdateMember={updateMember}
          onCreateIssuer={createIssuer}
          onCreateSequence={createSequence}
          onUploadCertificate={uploadCertificate}
          issuers={issuers}
          modalError={modalError}
        />
      )}
    </div>
  );
}

function firstApiError(data) {
  if (!data || typeof data !== 'object') return '';
  const firstKey = Object.keys(data)[0];
  const value = data[firstKey];
  if (Array.isArray(value)) return value[0];
  if (typeof value === 'string') return value;
  return '';
}

function buildFiscalChecklist(company, issuers, sequences) {
  const companyFields = [company?.name, company?.legal_name, company?.email, company?.phone, company?.address];
  const companyComplete = companyFields.every((value) => String(value || '').trim());
  const hasRnc = Boolean(String(company?.rnc || '').trim());
  const hasIssuer = issuers.length > 0;
  const hasActiveIssuer = issuers.some((issuer) => issuer.is_active);
  const certificateStatuses = issuers.map((issuer) => issuer.certificate_status || 'missing');
  const hasActiveCertificate = certificateStatuses.includes('active');
  const hasCertificateAttention = certificateStatuses.some((status) => ['expired', 'invalid', 'expiring_soon'].includes(status));

  return [
    {
      id: 'company_data',
      label: 'Datos empresa completos',
      description: 'Nombre, razón social, contacto y dirección.',
      state: companyComplete ? 'complete' : 'pending',
      actionLabel: 'Completar datos',
    },
    {
      id: 'company_rnc',
      label: 'RNC configurado',
      description: 'Identificación fiscal de la empresa activa.',
      state: hasRnc ? 'complete' : 'pending',
      actionLabel: 'Configurar RNC',
    },
    {
      id: 'issuer',
      label: 'Emisor fiscal configurado',
      description: 'Registro e-CF autorizado para la empresa.',
      state: hasActiveIssuer ? 'complete' : hasIssuer ? 'attention' : 'pending',
      actionLabel: 'Configurar emisor',
    },
    {
      id: 'certificate',
      label: 'Certificado DGII cargado',
      description: 'Certificado digital del emisor para firma e-CF.',
      state: hasActiveCertificate ? 'complete' : hasCertificateAttention ? 'attention' : 'pending',
      actionLabel: 'Configurar certificado',
    },
    sequenceChecklistItem('31', 'Secuencias E31 configuradas', sequences),
    sequenceChecklistItem('32', 'Secuencias E32 configuradas', sequences),
    sequenceChecklistItem('34', 'Secuencias E34 configuradas', sequences),
  ];
}

function sequenceChecklistItem(ecfType, label, sequences) {
  const typeSequences = sequences.filter((sequence) => sequence.ecf_type === ecfType);
  const hasActive = typeSequences.some((sequence) => sequence.is_active);
  return {
    id: `sequence_${ecfType}`,
    label,
    description: `Rangos autorizados e-CF ${ecfType}.`,
    state: hasActive ? 'complete' : typeSequences.length > 0 ? 'attention' : 'pending',
    actionLabel: `Configurar E${ecfType}`,
  };
}

function CompanyTabs({ activeTab, onChange }) {
  const tabs = [
    { id: 'summary', label: 'Resumen' },
    { id: 'fiscal', label: 'Fiscal / DGII' },
    { id: 'sequences', label: 'Secuencias' },
    { id: 'members', label: 'Miembros' },
  ];

  return (
    <nav className="company-tabs" aria-label="Secciones de empresa">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={activeTab === tab.id ? 'active' : ''}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

function IssuerSection({
  issuers,
  alerts,
  canManage,
  refProp,
  onCreateIssuer,
  onViewDetails,
  onViewSequences,
  onConfigureCertificate,
}) {
  return (
    <section className="company-section" ref={refProp}>
      <div className="company-section-heading">
        <div>
          <span className="company-kicker">DGII</span>
          <h2>Emisor fiscal y certificados</h2>
        </div>
        {canManage && (
          <button type="button" className="company-section-action" onClick={onCreateIssuer}>
            <Plus size={15} strokeWidth={1.8} />
            Configurar emisor
          </button>
        )}
      </div>

      {alerts.length > 0 && (
        <div className="company-alert-list">
          {alerts.map((alert) => (
            <div key={alert.id} className={`company-inline-alert ${alert.tone}`}>
              <AlertTriangle size={18} strokeWidth={1.8} />
              <div>
                <strong>{alert.issuerName}</strong>
                <span>{alert.message}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {issuers.length === 0 ? (
        <EmptyState
          title="Sin emisor fiscal configurado"
          text="Crea un emisor e-CF para que el POS pueda generar documentos fiscales en modo mock o pruebas."
        />
      ) : (
        <div className="issuer-list">
          {issuers.map((issuer) => (
            <IssuerCard
              key={issuer.id}
              issuer={issuer}
              onViewDetails={() => onViewDetails(issuer)}
              onViewSequences={onViewSequences}
              onConfigureCertificate={onConfigureCertificate}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function CompanyInfoCard({ company, refProp }) {
  return (
    <article className="company-card company-info-card" ref={refProp}>
      <header>
        <span className="company-card-icon"><Building2 size={20} strokeWidth={1.8} /></span>
        <div>
          <h2>Información de empresa</h2>
          <p>Datos visibles para operación interna y documentos.</p>
        </div>
      </header>

      <div className="company-profile">
        <div className="company-logo-box">
          {company?.logo_url ? (
            <img src={company.logo_url} alt={company?.name || 'Logo empresa'} />
          ) : (
            <span>{(company?.name || 'E').charAt(0).toUpperCase()}</span>
          )}
        </div>
        <div>
          <strong>{company?.legal_name || company?.name || 'Sin empresa activa'}</strong>
          <span>{company?.role_label || 'Rol no disponible'}</span>
        </div>
      </div>

      <dl className="company-facts">
        <Fact icon={IdCard} label="RNC" value={company?.rnc || 'No configurado'} />
        <Fact icon={Mail} label="Email" value={company?.email || 'No configurado'} />
        <Fact icon={Phone} label="Teléfono" value={company?.phone || 'No configurado'} />
        <Fact icon={Building2} label="Dirección" value={company?.address || 'No configurada'} />
      </dl>
    </article>
  );
}

function IssuerSummary({ issuers, sequences }) {
  const active = issuers.filter((issuer) => issuer.is_active).length;
  const certificatesOk = issuers.filter((issuer) => issuer.certificate_status === 'active').length;
  const attention = issuers.filter((issuer) => issuer.certificate_status && issuer.certificate_status !== 'active').length;

  return (
    <article className="company-card">
      <header>
        <span className="company-card-icon"><ShieldCheck size={20} strokeWidth={1.8} /></span>
        <div>
          <h2>Resumen fiscal</h2>
          <p>Estado rápido por empresa activa.</p>
        </div>
      </header>

      <div className="issuer-summary-grid">
        <SummaryStat label="Emisores" value={issuers.length} />
        <SummaryStat label="Activos" value={active} />
        <SummaryStat label="Certificados OK" value={certificatesOk} />
        <SummaryStat label="Secuencias" value={sequences.length} />
        <SummaryStat label="Requieren atención" value={attention} tone={attention > 0 ? 'danger' : 'success'} />
      </div>
    </article>
  );
}

function FiscalOnboardingChecklist({ items, actions }) {
  return (
    <section className="company-section">
      <div className="company-section-heading">
        <div>
          <span className="company-kicker">Onboarding fiscal</span>
          <h2>Preparación e-CF de la empresa</h2>
        </div>
      </div>
      <div className="fiscal-checklist">
        {items.map((item) => (
          <div key={item.label} className={`fiscal-check-item ${item.state}`}>
            <span className="fiscal-check-icon">
              {item.state === 'complete' ? <CheckCircle2 size={18} strokeWidth={1.9} /> : <CircleDashed size={18} strokeWidth={1.9} />}
            </span>
            <div>
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </div>
            <div className="fiscal-check-actions">
              <em>{item.state === 'complete' ? 'Completo' : item.state === 'attention' ? 'Requiere atención' : 'Pendiente'}</em>
              {item.state !== 'complete' && (
                <button type="button" onClick={() => actions[item.id]?.()}>
                  {item.actionLabel}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function NextStepsCard() {
  const steps = [
    'Completar datos empresa.',
    'Configurar emisor DGII.',
    'Cargar certificado.',
    'Configurar secuencias E31/E32/E34.',
    'Probar emisión en ambiente de pruebas.',
  ];

  return (
    <section className="company-section">
      <div className="company-section-heading">
        <div>
          <span className="company-kicker">Próximos pasos</span>
          <h2>Orden recomendado de configuración</h2>
        </div>
      </div>
      <ol className="next-steps-list">
        {steps.map((step, index) => (
          <li key={step}>
            <span>{index + 1}</span>
            <strong>{step}</strong>
          </li>
        ))}
      </ol>
    </section>
  );
}

function IssuerCard({ issuer, onViewDetails, onViewSequences, onConfigureCertificate }) {
  const status = issuer.certificate_status || 'missing';
  const meta = certificateStatusMeta[status] || certificateStatusMeta.invalid;
  const rncMatchStatus = issuer.certificate_rnc_match_status || 'unknown';
  const rncMatchMeta = certificateRncMatchMeta[rncMatchStatus] || certificateRncMatchMeta.unknown;

  return (
    <article className="issuer-card">
      <header>
        <div>
          <h3>{issuer.business_name || issuer.trade_name || 'Emisor fiscal'}</h3>
          <p>RNC {issuer.rnc || 'No configurado'} · {environmentLabels[issuer.environment] || issuer.environment || 'Ambiente no definido'}</p>
        </div>
        <div className="issuer-badges">
          <span className={`issuer-active ${issuer.is_active ? 'yes' : 'no'}`}>
            {issuer.is_active ? 'Activo' : 'Inactivo'}
          </span>
          <CertificateStatusBadge status={status} />
          <span className={`certificate-rnc-match ${rncMatchMeta.tone}`}>
            RNC: {rncMatchMeta.label}
          </span>
        </div>
      </header>

      <div className="issuer-actions">
        <button type="button" onClick={onViewDetails}>Ver detalles</button>
        <button type="button" onClick={onViewSequences}>Ver secuencias</button>
        <button type="button" disabled title="Disponible en próxima fase">Refrescar metadata</button>
        <button type="button" onClick={onConfigureCertificate}>Configurar certificado</button>
      </div>

      <div className="certificate-panel">
        <div className={`certificate-status-block ${meta.tone}`}>
          <BadgeCheck size={22} strokeWidth={1.8} />
          <div>
            <strong>{meta.label}</strong>
            <span>Actualizado {formatDate(issuer.certificate_status_updated_at, true)}</span>
            <small>{meta.action}</small>
          </div>
        </div>

        <dl className="certificate-grid">
          <CertificateField label="Subject" value={issuer.certificate_subject} />
          <CertificateField label="Issuer" value={issuer.certificate_issuer} />
          <CertificateField label="Serial number" value={issuer.certificate_serial_number} />
          <CertificateField label="Fingerprint" value={compactFingerprint(issuer.certificate_fingerprint)} title={issuer.certificate_fingerprint} />
          <CertificateField label="RNC detectado" value={issuer.certificate_rnc_detected} />
          <CertificateField label="Coincidencia RNC" value={rncMatchMeta.label} />
          <CertificateField label="Válido desde" value={formatDate(issuer.certificate_not_valid_before)} />
          <CertificateField label="Válido hasta" value={formatDate(issuer.certificate_not_valid_after)} />
        </dl>
        {rncMatchStatus === 'mismatch' && (
          <div className="company-inline-alert danger">
            <CircleAlert size={16} strokeWidth={1.8} />
            <div>
              <strong>RNC del certificado no coincide</strong>
              <span>El RNC detectado en el certificado no coincide con el RNC del emisor.</span>
            </div>
          </div>
        )}
      </div>

      <CertificateHistory certificates={issuer.certificates || []} />
    </article>
  );
}

function CertificateHistory({ certificates }) {
  if (!certificates.length) {
    return (
      <div className="certificate-history empty">
        <strong>Historial de certificados</strong>
        <span>No hay certificados históricos registrados para este emisor.</span>
      </div>
    );
  }

  return (
    <div className="certificate-history">
      <div className="certificate-history-header">
        <strong>Historial de certificados</strong>
        <span>{certificates.length} registro{certificates.length === 1 ? '' : 's'}</span>
      </div>
      <div className="certificate-history-list">
        {certificates.map((certificate) => {
          const statusMeta = certificateStatusMeta[certificate.status || 'missing'] || certificateStatusMeta.invalid;
          const rncMeta = certificateRncMatchMeta[certificate.rnc_match_status || 'unknown'] || certificateRncMatchMeta.unknown;
          return (
            <article key={certificate.id} className={`certificate-history-item ${certificate.is_active ? 'active' : ''}`}>
              <div>
                <span className={`certificate-badge ${statusMeta.tone}`}>{statusMeta.label}</span>
                {certificate.is_active && <span className="issuer-active yes">Activo</span>}
                {certificate.storage_backend === 'legacy_local' && <span className="issuer-active no">Legacy/backfill</span>}
              </div>
              <dl className="certificate-grid">
                <CertificateField label="Fingerprint" value={compactFingerprint(certificate.fingerprint)} title={certificate.fingerprint} />
                <CertificateField label="Válido desde" value={formatDate(certificate.not_valid_before)} />
                <CertificateField label="Válido hasta" value={formatDate(certificate.not_valid_after)} />
                <CertificateField label="RNC match" value={rncMeta.label} />
                <CertificateField label="Subido" value={formatDate(certificate.uploaded_at, true)} />
                <CertificateField label="Almacenamiento" value={certificate.storage_backend} />
              </dl>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function SequenceSection({ sequences, canManage, refProp, onCreateSequence }) {
  return (
    <section className="company-section" ref={refProp}>
      <div className="company-section-heading">
        <div>
          <span className="company-kicker">Secuencias e-CF</span>
          <h2>Rangos autorizados por DGII</h2>
        </div>
        {canManage && (
          <div className="company-section-actions">
            {['31', '32', '34'].map((type) => (
              <button
                key={type}
                type="button"
                className="company-section-action"
                onClick={() => onCreateSequence(type)}
              >
                <Plus size={15} strokeWidth={1.8} />
                Configurar E{type}
              </button>
            ))}
          </div>
        )}
      </div>

      {sequences.length === 0 ? (
        <EmptyState
          title="Sin secuencias e-CF configuradas"
          text="Cuando registres rangos E31, E32 o E34, aparecerán aquí para seguimiento operativo."
        />
      ) : (
        <div className="sequence-table-wrap">
          <table className="sequence-table">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Rango</th>
                <th>Próximo</th>
                <th>Vencimiento</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {sequences.map((sequence) => (
                <tr key={sequence.id}>
                  <td>
                    <span className="sequence-type">
                      <FileKey2 size={15} strokeWidth={1.8} />
                      E{sequence.ecf_type}
                    </span>
                  </td>
                  <td>{sequence.start_number} - {sequence.end_number}</td>
                  <td>{sequence.next_number}</td>
                  <td>{formatDate(sequence.expiration_date)}</td>
                  <td>
                    <span className={`issuer-active ${sequence.is_active ? 'yes' : 'no'}`}>
                      {sequence.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function CompanyInfoModal({
  modal,
  saving,
  onClose,
  onSaveCompany,
  onCreateCompany,
  onAddMember,
  onUpdateMember,
  onCreateIssuer,
  onCreateSequence,
  onUploadCertificate,
  issuers,
  modalError,
}) {
  const issuer = modal.issuer;
  const isCompanyForm = ['company-edit', 'company-create'].includes(modal.type);
  const isMemberForm = ['member-add', 'member-edit'].includes(modal.type);
  const isIssuerForm = modal.type === 'issuer-create';
  const isSequenceForm = modal.type === 'sequence-create';
  const isCertificateUpload = modal.type === 'certificate-upload';

  return (
    <div className="company-modal-backdrop" role="presentation" onClick={onClose}>
      <div className="company-modal" role="dialog" aria-modal="true" aria-labelledby="company-modal-title" onClick={(event) => event.stopPropagation()}>
        <header>
          <div>
            <span className="company-kicker">
              {modal.type === 'issuer'
                ? 'Detalles del emisor'
                : isCompanyForm || isMemberForm
                  ? 'Gestión multiempresa'
                  : isIssuerForm || isSequenceForm || isCertificateUpload
                  ? 'Gestión multiempresa'
                  : 'Próxima fase'}
            </span>
            <h2 id="company-modal-title">{modal.title}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar">
            <X size={18} strokeWidth={1.8} />
          </button>
        </header>

        {isCompanyForm ? (
          <CompanyForm
            initialValues={modal.company}
            saving={saving}
            submitLabel={modal.type === 'company-create' ? 'Crear empresa' : 'Guardar cambios'}
            onSubmit={modal.type === 'company-create' ? onCreateCompany : onSaveCompany}
          />
        ) : isMemberForm ? (
          <MemberForm
            member={modal.member}
            mode={modal.type}
            saving={saving}
            apiError={modalError}
            onSubmit={(form) => {
              if (modal.type === 'member-add') {
                onAddMember(form);
              } else {
                onUpdateMember(modal.member.id, form);
              }
            }}
          />
        ) : isIssuerForm ? (
          <IssuerForm
            issuer={modal.issuer}
            saving={saving}
            apiError={modalError}
            onSubmit={onCreateIssuer}
          />
        ) : isSequenceForm ? (
          <SequenceForm
            sequence={modal.sequence}
            issuers={issuers}
            saving={saving}
            apiError={modalError}
            onSubmit={onCreateSequence}
          />
        ) : isCertificateUpload ? (
          <CertificateUploadForm
            issuer={modal.issuer}
            saving={saving}
            apiError={modalError}
            onSubmit={(form) => onUploadCertificate(modal.issuer.id, form)}
          />
        ) : modal.type === 'issuer' && issuer ? (
          <dl className="modal-detail-grid">
            <CertificateField label="Razón social" value={issuer.business_name} />
            <CertificateField label="Nombre comercial" value={issuer.trade_name} />
            <CertificateField label="RNC" value={issuer.rnc} />
            <CertificateField label="Ambiente" value={environmentLabels[issuer.environment] || issuer.environment} />
            <CertificateField label="Certificado" value={certificateStatusMeta[issuer.certificate_status || 'missing']?.label} />
            <CertificateField label="Actualizado" value={formatDate(issuer.certificate_status_updated_at, true)} />
            <CertificateField label="RNC detectado" value={issuer.certificate_rnc_detected} />
            <CertificateField
              label="Coincidencia RNC"
              value={certificateRncMatchMeta[issuer.certificate_rnc_match_status || 'unknown']?.label}
            />
            <CertificateField label="Subject" value={issuer.certificate_subject} />
            <CertificateField label="Issuer" value={issuer.certificate_issuer} />
          </dl>
        ) : (
          <p className="company-modal-message">{modal.message || 'Disponible en próxima fase.'}</p>
        )}

        {!isCompanyForm && !isMemberForm && !isIssuerForm && !isSequenceForm && !isCertificateUpload && (
          <footer>
            <button type="button" onClick={onClose}>
              Entendido
              <ArrowRight size={15} strokeWidth={1.8} />
            </button>
          </footer>
        )}
      </div>
    </div>
  );
}

function CertificateUploadForm({ issuer, saving, apiError, onSubmit }) {
  const [form, setForm] = useState({ certificate: null, password: '' });
  const [localError, setLocalError] = useState('');

  const submit = (event) => {
    event.preventDefault();
    if (!form.certificate) {
      setLocalError('Selecciona un archivo .p12 del certificado DGII.');
      return;
    }
    if (!form.certificate.name.toLowerCase().endsWith('.p12')) {
      setLocalError('El certificado debe ser un archivo .p12.');
      return;
    }
    if (!String(form.password || '').trim()) {
      setLocalError('La contraseña del certificado es obligatoria para extraer metadata.');
      return;
    }
    setLocalError('');
    onSubmit(form);
  };

  return (
    <form className="company-form" onSubmit={submit}>
      {(localError || apiError) && (
        <div className="company-form-error" tabIndex="-1">
          <CircleAlert size={16} strokeWidth={1.8} />
          {localError || apiError}
        </div>
      )}

      <div className="company-inline-alert warning">
        <AlertTriangle size={17} strokeWidth={1.8} />
        <div>
          <strong>Implementación transitoria</strong>
          <span>Este certificado será usado para futuras firmas. El password aún se conserva de forma legacy hasta migrar a almacenamiento seguro.</span>
        </div>
      </div>

      <div className="company-form-grid">
        <label>
          <span>Emisor</span>
          <input value={`${issuer?.business_name || issuer?.trade_name || 'Emisor fiscal'} · ${issuer?.rnc || ''}`} disabled />
        </label>
        <label>
          <span>Archivo .p12 *</span>
          <input
            type="file"
            accept=".p12,application/x-pkcs12"
            onChange={(event) => setForm((current) => ({ ...current, certificate: event.target.files?.[0] || null }))}
          />
          <small>No se imprime la ruta ni la contraseña en logs.</small>
        </label>
        <label>
          <span>Contraseña *</span>
          <input
            type="password"
            value={form.password}
            onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            placeholder="Contraseña del .p12"
            autoComplete="new-password"
          />
          <small>Si la contraseña es incorrecta, el estado quedará como inválido.</small>
        </label>
      </div>

      <div className="company-form-actions">
        <button type="submit" disabled={saving}>
          {saving ? <RefreshCw size={15} strokeWidth={1.8} /> : <FileKey2 size={15} strokeWidth={1.8} />}
          {saving ? 'Cargando...' : 'Cargar certificado'}
        </button>
      </div>
    </form>
  );
}

function MemberForm({ member, mode, saving, apiError, onSubmit }) {
  const [form, setForm] = useState(() => ({
    email: member?.email || '',
    role: member?.role || 'cashier',
    is_active: member?.is_active ?? true,
  }));
  const [localError, setLocalError] = useState('');
  const isEdit = mode === 'member-edit';

  const submit = (event) => {
    event.preventDefault();
    if (!isEdit && !String(form.email || '').trim()) {
      setLocalError('El email del usuario es obligatorio.');
      return;
    }
    setLocalError('');
    onSubmit(isEdit ? { role: form.role, is_active: form.is_active } : { email: form.email, role: form.role });
  };

  return (
    <form className="company-form" onSubmit={submit}>
      {(localError || apiError) && (
        <div className="company-form-error" tabIndex="-1">
          <CircleAlert size={16} strokeWidth={1.8} />
          {localError || apiError}
        </div>
      )}

      <div className="company-form-grid">
        <label>
          <span>Email del usuario {!isEdit && '*'}</span>
          <input
            type="email"
            value={form.email}
            disabled={isEdit}
            onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
            placeholder="usuario@empresa.com"
          />
          {!isEdit && <small>El usuario debe existir antes de agregarlo.</small>}
        </label>
        <label>
          <span>Rol</span>
          <select value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}>
            {membershipRoleOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        {isEdit && (
          <label className="company-form-check">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
            />
            <span>Membership activo</span>
          </label>
        )}
      </div>

      <div className="company-form-actions">
        <button type="submit" disabled={saving}>
          {saving ? <RefreshCw size={15} strokeWidth={1.8} /> : <Save size={15} strokeWidth={1.8} />}
          {saving ? 'Guardando...' : isEdit ? 'Guardar miembro' : 'Agregar miembro'}
        </button>
      </div>
    </form>
  );
}

function IssuerForm({ issuer, saving, apiError, onSubmit }) {
  const [form, setForm] = useState(() => ({
    business_name: issuer?.business_name || '',
    trade_name: issuer?.trade_name || '',
    rnc: issuer?.rnc || '',
    environment: issuer?.environment || 'testing',
    is_active: issuer?.is_active ?? true,
  }));
  const [localError, setLocalError] = useState('');

  const patch = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const submit = (event) => {
    event.preventDefault();
    if (!String(form.business_name || '').trim()) {
      setLocalError('La razón social del emisor es obligatoria.');
      return;
    }
    if (!String(form.rnc || '').trim()) {
      setLocalError('El RNC del emisor es obligatorio.');
      return;
    }
    const rncError = validateRnc(form.rnc, { required: true, label: 'RNC del emisor' });
    if (rncError) {
      setLocalError(rncError);
      return;
    }
    setLocalError('');
    onSubmit(form);
  };

  return (
    <form className="company-form" onSubmit={submit}>
      {(localError || apiError) && (
        <div className="company-form-error" tabIndex="-1">
          <CircleAlert size={16} strokeWidth={1.8} />
          {localError || apiError}
        </div>
      )}

      <div className="company-form-grid">
        <label>
          <span>Razón social *</span>
          <input value={form.business_name} onChange={(event) => patch('business_name', event.target.value)} placeholder="Razón social del emisor" />
        </label>
        <label>
          <span>Nombre comercial</span>
          <input value={form.trade_name} onChange={(event) => patch('trade_name', event.target.value)} placeholder="Nombre comercial" />
        </label>
        <label>
          <span>RNC *</span>
          <input
            value={form.rnc}
            onChange={(event) => patch('rnc', normalizeRncInput(event.target.value))}
            placeholder="RNC del emisor"
            inputMode="numeric"
            maxLength={11}
          />
          <small>Solo numeros, 9 u 11 digitos.</small>
        </label>
        <label>
          <span>Ambiente</span>
          <select value={form.environment} onChange={(event) => patch('environment', event.target.value)}>
            <option value="testing">Testing</option>
            <option value="production">Production</option>
          </select>
        </label>
        <label className="company-form-check">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => patch('is_active', event.target.checked)}
          />
          <span>Emisor activo</span>
        </label>
      </div>

      <div className="company-form-actions">
        <button type="submit" disabled={saving}>
          {saving ? <RefreshCw size={15} strokeWidth={1.8} /> : <Save size={15} strokeWidth={1.8} />}
          {saving ? 'Guardando...' : 'Crear emisor'}
        </button>
      </div>
    </form>
  );
}

function SequenceForm({ sequence, issuers, saving, apiError, onSubmit }) {
  const [form, setForm] = useState(() => ({
    issuer: sequence?.issuer || '',
    ecf_type: sequence?.ecf_type || '31',
    start_number: sequence?.start_number || 1,
    end_number: sequence?.end_number || 100,
    next_number: sequence?.next_number || sequence?.start_number || 1,
    expiration_date: sequence?.expiration_date || '',
    is_active: sequence?.is_active ?? true,
  }));
  const [localError, setLocalError] = useState('');

  const patch = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const submit = (event) => {
    event.preventDefault();
    if (!form.issuer) {
      setLocalError('Primero debes seleccionar un emisor fiscal activo.');
      return;
    }
    if (Number(form.start_number) <= 0 || Number(form.end_number) <= 0) {
      setLocalError('Los números de secuencia deben ser mayores a cero.');
      return;
    }
    if (Number(form.start_number) > Number(form.end_number)) {
      setLocalError('El número final debe ser mayor o igual al inicial.');
      return;
    }
    if (Number(form.next_number) < Number(form.start_number) || Number(form.next_number) > Number(form.end_number)) {
      setLocalError('El próximo número debe estar dentro del rango configurado.');
      return;
    }
    if (!String(form.expiration_date || '').trim()) {
      setLocalError('La fecha de vencimiento de la secuencia es obligatoria para el onboarding fiscal.');
      return;
    }
    setLocalError('');
    onSubmit({
      ...form,
      start_number: Number(form.start_number),
      end_number: Number(form.end_number),
      next_number: Number(form.next_number),
    });
  };

  return (
    <form className="company-form" onSubmit={submit}>
      {(localError || apiError || issuers.length === 0) && (
        <div className="company-form-error" tabIndex="-1">
          <CircleAlert size={16} strokeWidth={1.8} />
          {localError || apiError || 'Debes crear un emisor fiscal antes de configurar secuencias.'}
        </div>
      )}

      <div className="company-form-grid">
        <label>
          <span>Emisor asociado *</span>
          <select value={form.issuer} onChange={(event) => patch('issuer', event.target.value)} disabled={issuers.length === 0}>
            <option value="">Seleccionar emisor</option>
            {issuers.map((issuer) => (
              <option key={issuer.id} value={issuer.id}>
                {issuer.business_name || issuer.trade_name || issuer.rnc} · {issuer.rnc}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Tipo e-CF</span>
          <select value={form.ecf_type} onChange={(event) => patch('ecf_type', event.target.value)}>
            <option value="31">E31 - Factura crédito fiscal</option>
            <option value="32">E32 - Factura consumo</option>
            <option value="34">E34 - Nota de crédito</option>
          </select>
        </label>
        <label>
          <span>Número inicial *</span>
          <input type="number" min="1" value={form.start_number} onChange={(event) => patch('start_number', event.target.value)} />
        </label>
        <label>
          <span>Número final *</span>
          <input type="number" min="1" value={form.end_number} onChange={(event) => patch('end_number', event.target.value)} />
        </label>
        <label>
          <span>Próximo número *</span>
          <input type="number" min="1" value={form.next_number} onChange={(event) => patch('next_number', event.target.value)} />
        </label>
        <label>
          <span>Fecha vencimiento *</span>
          <input type="date" value={form.expiration_date || ''} onChange={(event) => patch('expiration_date', event.target.value)} required />
          <small>Requerida para operar con rangos autorizados DGII.</small>
        </label>
        <label className="company-form-check">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => patch('is_active', event.target.checked)}
          />
          <span>Secuencia activa</span>
        </label>
      </div>

      <div className="company-form-actions">
        <button type="submit" disabled={saving || issuers.length === 0}>
          {saving ? <RefreshCw size={15} strokeWidth={1.8} /> : <Save size={15} strokeWidth={1.8} />}
          {saving ? 'Guardando...' : 'Crear secuencia'}
        </button>
      </div>
    </form>
  );
}

function CompanyForm({ initialValues, saving, submitLabel, onSubmit }) {
  const [form, setForm] = useState(() => ({
    name: initialValues?.name || '',
    legal_name: initialValues?.legal_name || '',
    rnc: initialValues?.rnc || '',
    email: initialValues?.email || '',
    phone: initialValues?.phone || '',
    address: initialValues?.address || '',
    primary_color: initialValues?.primary_color || '',
  }));
  const [localError, setLocalError] = useState('');

  const patch = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  const submit = (event) => {
    event.preventDefault();
    if (!String(form.name || '').trim()) {
      setLocalError('El nombre comercial es obligatorio.');
      return;
    }
    const rncError = validateRnc(form.rnc, { label: 'RNC de la empresa' });
    if (rncError) {
      setLocalError(rncError);
      return;
    }
    const phoneError = validatePhone(form.phone, { label: 'Telefono de la empresa' });
    if (phoneError) {
      setLocalError(phoneError);
      return;
    }
    setLocalError('');
    onSubmit(form);
  };

  return (
    <form className="company-form" onSubmit={submit}>
      {localError && (
        <div className="company-form-error">
          <CircleAlert size={16} strokeWidth={1.8} />
          {localError}
        </div>
      )}

      <div className="company-form-grid">
        <label>
          <span>Nombre comercial *</span>
          <input value={form.name} onChange={(event) => patch('name', event.target.value)} placeholder="Ej: Percy Technology" />
        </label>
        <label>
          <span>Razón social</span>
          <input value={form.legal_name} onChange={(event) => patch('legal_name', event.target.value)} placeholder="Ej: Percy Technology SRL" />
        </label>
        <label>
          <span>RNC</span>
          <input
            value={form.rnc}
            onChange={(event) => patch('rnc', normalizeRncInput(event.target.value))}
            placeholder="RNC de la empresa"
            inputMode="numeric"
            maxLength={11}
          />
          <small>Requerido para completar la configuración fiscal.</small>
        </label>
        <label>
          <span>Email</span>
          <input type="email" value={form.email || ''} onChange={(event) => patch('email', event.target.value)} placeholder="empresa@dominio.com" />
        </label>
        <label>
          <span>Teléfono</span>
          <input value={form.phone} onChange={(event) => patch('phone', event.target.value)} placeholder="809 000 0000" maxLength={20} />
          <small>Puede incluir espacios, guiones, parentesis o +.</small>
        </label>
        <label>
          <span>Color primario</span>
          <input value={form.primary_color} onChange={(event) => patch('primary_color', event.target.value)} placeholder="#6C63FF" />
        </label>
        <label className="company-form-wide">
          <span>Dirección</span>
          <textarea value={form.address} onChange={(event) => patch('address', event.target.value)} placeholder="Dirección fiscal/comercial" rows={3} />
        </label>
      </div>

      <div className="company-form-actions">
        <button type="submit" disabled={saving}>
          {saving ? <RefreshCw size={15} strokeWidth={1.8} /> : <Save size={15} strokeWidth={1.8} />}
          {saving ? 'Guardando...' : submitLabel}
        </button>
      </div>
    </form>
  );
}

function CompanyMembersSection({ members, canManage, onAddMember, onEditMember, onToggleMember }) {
  return (
    <section className="company-section">
      <div className="company-section-heading">
        <div>
          <span className="company-kicker">Equipo</span>
          <h2>Miembros de la empresa</h2>
        </div>
        {canManage && (
          <button type="button" className="company-section-action" onClick={onAddMember}>
            <Plus size={15} strokeWidth={1.8} />
            Agregar miembro
          </button>
        )}
      </div>

      {members.length === 0 ? (
        <EmptyState title="Sin miembros visibles" text="Cuando existan usuarios vinculados a esta empresa, aparecerán aquí en modo solo lectura." />
      ) : (
        <div className="company-members-wrap">
          <table className="company-members-table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Email</th>
                <th>Rol</th>
                <th>Estado</th>
                {canManage && <th>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.id}>
                  <td data-label="Usuario">
                    <span className="member-avatar">{(member.username || 'U').charAt(0).toUpperCase()}</span>
                    <span>
                      <strong>{[member.first_name, member.last_name].filter(Boolean).join(' ') || member.username}</strong>
                      <small>{member.username}</small>
                    </span>
                  </td>
                  <td data-label="Email">{member.email || 'No configurado'}</td>
                  <td data-label="Rol">{member.role_label || member.role}</td>
                  <td data-label="Estado">
                    <span className={`issuer-active ${member.is_active ? 'yes' : 'no'}`}>
                      {member.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  {canManage && (
                    <td data-label="Acciones">
                      <div className="member-actions">
                        <button type="button" onClick={() => onEditMember(member)}>
                          Editar
                        </button>
                        <button type="button" onClick={() => onToggleMember(member)}>
                          {member.is_active ? 'Desactivar' : 'Activar'}
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function CertificateStatusBadge({ status }) {
  const meta = certificateStatusMeta[status] || certificateStatusMeta.invalid;
  return <span className={`certificate-badge ${meta.tone}`}>{meta.label}</span>;
}

function SummaryStat({ label, value, tone = 'neutral' }) {
  return (
    <div className={`summary-stat ${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function Fact({ icon: Icon, label, value }) {
  return (
    <div>
      <dt><Icon size={15} strokeWidth={1.8} /> {label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function CertificateField({ label, value, title }) {
  return (
    <div title={title || value || ''}>
      <dt>{label}</dt>
      <dd>{value || 'No disponible'}</dd>
    </div>
  );
}

function EmptyState({ title, text }) {
  return (
    <div className="company-empty-state">
      <ListChecks size={26} strokeWidth={1.7} />
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}
