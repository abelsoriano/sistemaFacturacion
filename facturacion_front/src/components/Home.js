import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  ChartNoAxesColumnIncreasing,
  FileText,
  KeyRound,
  Receipt,
  ReceiptText,
  RefreshCw,
  ShieldCheck,
  ShoppingCart,
  Zap,
} from 'lucide-react';

import api from '../services/api';
import { ecfApi } from '../services/ecf/ecfApi';
import {
  FINANCIAL_TOTALS_PERMISSIONS,
  ROUTE_PERMISSIONS,
  userHasAnyPermission,
  userHasPermissions,
} from '../utils/permissions';
import '../css/Home.css';

const money = (value) => `$${Number(value || 0).toLocaleString('es-DO', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})}`;

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

const todayKey = () => new Date().toISOString().slice(0, 10);

function Home() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(() => JSON.parse(localStorage.getItem('user') || '{}'));
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [recentInvoices, setRecentInvoices] = useState([]);
  const [ecfMonitor, setEcfMonitor] = useState(null);
  const [e34Summary, setE34Summary] = useState(null);
  const [issuers, setIssuers] = useState([]);
  const [sequences, setSequences] = useState([]);
  const [errors, setErrors] = useState([]);

  const canViewFinancialTotals = userHasAnyPermission(currentUser, FINANCIAL_TOTALS_PERMISSIONS);

  const canOpen = (route) => userHasPermissions(currentUser, ROUTE_PERMISSIONS[route] || []);

  useEffect(() => {
    setCurrentUser(JSON.parse(localStorage.getItem('user') || '{}'));
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const nextErrors = [];

      const requests = [
        (canOpen('/dashboard')
          ? api.get('/dashboard/')
              .then((response) => setDashboard(response.data))
              .catch(() => nextErrors.push('Dashboard'))
          : Promise.resolve()),
        (canOpen('/invoice-list')
          ? api.get('/invoices/')
              .then((response) => setRecentInvoices(normalizeList(response.data).slice(0, 6)))
              .catch(() => nextErrors.push('Facturas'))
          : Promise.resolve()),
        (canOpen('/ecf')
          ? ecfApi.getMonitor()
              .then((data) => setEcfMonitor(data))
              .catch(() => nextErrors.push('e-CF'))
          : Promise.resolve()),
        (canOpen('/ecf')
          ? api.get('/credit-notes/fiscal-summary/')
              .then((response) => setE34Summary(response.data))
              .catch(() => nextErrors.push('Notas E34'))
          : Promise.resolve()),
        (canOpen('/ecf')
          ? api.get('/ecf/issuers/')
              .then((response) => setIssuers(normalizeList(response.data)))
              .catch(() => nextErrors.push('Emisores DGII'))
          : Promise.resolve()),
        (canOpen('/ecf')
          ? api.get('/ecf/sequences/')
              .then((response) => setSequences(normalizeList(response.data)))
              .catch(() => nextErrors.push('Secuencias e-CF'))
          : Promise.resolve()),
      ];

      await Promise.all(requests);
      setErrors(nextErrors);
      setLoading(false);
    };

    load();
  }, [currentUser]); // eslint-disable-line react-hooks/exhaustive-deps

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Buenos días';
    if (hour < 19) return 'Buenas tardes';
    return 'Buenas noches';
  }, []);

  const userName = currentUser.first_name || currentUser.username || 'Usuario';
  const today = todayKey();
  const recentSales = dashboard?.recentSales || [];
  const todaySales = recentSales.filter((sale) => sale.date?.startsWith(today)).length;
  const invoicesPending = recentInvoices.filter((invoice) => invoice.status === 'pending').length;
  const lowStockCount = dashboard?.inventoryStatus?.low_stock_count || 0;
  const totalSales = dashboard?.salesSummary?.total_sales || 0;
  const acceptedEcf = ecfMonitor?.accepted || 0;
  const accountsReceivableCount = dashboard?.salesSummary?.accounts_receivable_count ?? invoicesPending;
  const acceptedFiscalCount = dashboard?.salesSummary?.accepted_fiscal_count ?? acceptedEcf;
  const submittedEcf = ecfMonitor?.pending_dgii || 0;
  const technicalFailed = ecfMonitor?.technical_failed || 0;
  const queuedJobs = ecfMonitor?.queued || ecfMonitor?.currently_queued || 0;
  const e34Pending = e34Summary?.pending || 0;
  const e34Review = e34Summary?.requires_manual_review || e34Summary?.inventory_compensation_required || 0;
  const certificateSummary = getCertificateSummary(issuers);
  const missingSequenceTypes = getMissingSequenceTypes(sequences);

  const quickActions = [
    {
      label: 'Nueva venta',
      description: 'Abrir POS',
      route: '/Fastsales',
      icon: Zap,
      permissionRoute: '/Fastsales',
    },
    {
      label: 'Nueva factura',
      description: 'Documento fiscal',
      route: '/create-invoice',
      icon: ReceiptText,
      permissionRoute: '/create-invoice',
    },
    {
      label: 'Cotización',
      description: 'Documento comercial',
      route: '/quotations/new',
      icon: FileText,
      permissionRoute: '/quotations/new',
    },
    {
      label: 'e-CF / DGII',
      description: 'Operación fiscal',
      route: '/ecf',
      icon: Receipt,
      permissionRoute: '/ecf',
    },
  ].filter((action) => canOpen(action.permissionRoute));

  const alerts = [
    lowStockCount > 0 && {
      id: 'low-stock',
      title: `${lowStockCount} productos bajo stock`,
      description: 'Revisa inventario crítico y reposición.',
      route: '/low-stock-report',
      tone: 'warning',
    },
    e34Pending > 0 && {
      id: 'e34-pending',
      title: `${e34Pending} notas E34 pendientes`,
      description: 'Hay notas de crédito esperando resolución fiscal.',
      route: '/ecf',
      tone: 'info',
    },
    e34Review > 0 && {
      id: 'e34-review',
      title: `${e34Review} notas requieren revisión`,
      description: 'Conciliación de inventario o revisión manual pendiente.',
      route: '/ecf',
      tone: 'danger',
    },
    technicalFailed > 0 && {
      id: 'technical-failed',
      title: `${technicalFailed} fallos técnicos e-CF`,
      description: 'Revisa retries, workers o comunicación DGII.',
      route: '/ecf',
      tone: 'danger',
    },
    certificateSummary.tone !== 'success' && {
      id: 'certificate-status',
      title: certificateSummary.title,
      description: certificateSummary.description,
      route: '/company?tab=fiscal',
      tone: certificateSummary.tone,
    },
    missingSequenceTypes.length > 0 && {
      id: 'missing-sequences',
      title: `Faltan secuencias ${missingSequenceTypes.join(', ')}`,
      description: 'Completa E31, E32 y E34 antes de operar fiscalmente.',
      route: '/company?tab=sequences',
      tone: 'warning',
    },
  ].filter(Boolean);

  return (
    <div className="hd-saas">
      <header className="hd-saas-header">
        <div>
          <span className="hd-kicker">{new Date().toLocaleDateString('es-DO', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
          <h1>{greeting}, {userName}</h1>
          <p>Resumen operativo de ventas, facturación fiscal e inventario.</p>
        </div>
        <button type="button" className="hd-primary-action" onClick={() => navigate('/Fastsales')} disabled={!canOpen('/Fastsales')}>
          <ShoppingCart size={17} strokeWidth={1.8} />
          Nueva venta
        </button>
      </header>

      {errors.length > 0 && (
        <div className="hd-inline-warning">
          <AlertTriangle size={16} strokeWidth={1.8} />
          Algunos datos no pudieron cargarse: {errors.join(', ')}.
        </div>
      )}

      <section className="hd-metrics-grid" aria-label="Resumen de negocio">
        <MetricCard
          icon={ShoppingCart}
          label="Ventas cobradas hoy"
          value={loading ? '...' : todaySales}
          caption="transacciones cobradas recientes"
        />
        <MetricCard
          icon={ReceiptText}
          label="Cuentas por cobrar"
          value={loading ? '...' : accountsReceivableCount}
          caption="facturas pendientes de cobro"
        />
        {canViewFinancialTotals && (
          <MetricCard
            icon={ChartNoAxesColumnIncreasing}
            label="Ingresos cobrados"
            value={loading ? '...' : money(totalSales)}
            caption="solo facturas pagadas"
          />
        )}
        <MetricCard
          icon={Receipt}
          label="Facturas aceptadas DGII"
          value={loading ? '...' : acceptedFiscalCount}
          caption={`${submittedEcf} enviados DGII`}
        />
      </section>

      <section className="hd-dashboard-grid">
        <Panel title="Facturas recientes" actionLabel="Ver facturas" onAction={() => navigate('/invoice-list')}>
          {recentInvoices.length === 0 ? (
            <EmptyState text={loading ? 'Cargando facturas...' : 'No hay facturas recientes disponibles.'} />
          ) : (
            <div className="hd-list">
              {recentInvoices.map((invoice) => (
                <button key={invoice.id} className="hd-list-row" type="button" onClick={() => navigate(`/invoices/${invoice.id}`)}>
                  <div>
                    <strong>{invoice.invoice_number || `Factura #${invoice.id}`}</strong>
                    <span>{invoice.client_name || invoice.customer_name || 'Consumidor Final'}</span>
                  </div>
                  <div className="hd-list-meta">
                    {canViewFinancialTotals && <strong>{money(invoice.total)}</strong>}
                    <span>{invoice.status || 'N/D'}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Accesos rápidos">
          {quickActions.length === 0 ? (
            <EmptyState text="No hay accesos disponibles para tus permisos." />
          ) : (
            <div className="hd-quick-grid">
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button key={action.route} type="button" className="hd-quick-card" onClick={() => navigate(action.route)}>
                    <Icon size={20} strokeWidth={1.8} />
                    <strong>{action.label}</strong>
                    <span>{action.description}</span>
                  </button>
                );
              })}
            </div>
          )}
        </Panel>

        <Panel title="Estado e-CF / DGII" actionLabel="Abrir e-CF" onAction={() => navigate('/ecf')}>
          {!ecfMonitor ? (
            <EmptyState text={loading ? 'Cargando operación fiscal...' : 'Sin datos e-CF disponibles.'} />
          ) : (
            <>
              <div className="hd-fiscal-grid">
                <FiscalPill label="Aceptados" value={acceptedEcf} tone="success" />
                <FiscalPill label="Enviados" value={submittedEcf} tone="info" />
                <FiscalPill label="En cola" value={queuedJobs} tone="neutral" />
                <FiscalPill label="Fallidos" value={technicalFailed} tone="danger" />
              </div>
              <div className="hd-fiscal-readiness">
                <ReadinessItem
                  icon={ShieldCheck}
                  label="Certificado DGII"
                  value={certificateSummary.shortLabel}
                  tone={certificateSummary.tone}
                />
                <ReadinessItem
                  icon={KeyRound}
                  label="Secuencias E31/E32/E34"
                  value={missingSequenceTypes.length === 0 ? 'Completas' : `Faltan ${missingSequenceTypes.join(', ')}`}
                  tone={missingSequenceTypes.length === 0 ? 'success' : 'warning'}
                />
              </div>
            </>
          )}
        </Panel>

        <Panel title="Alertas operativas">
          {alerts.length === 0 ? (
            <EmptyState text={loading ? 'Evaluando alertas...' : 'No hay alertas críticas en este momento.'} />
          ) : (
            <div className="hd-alert-list">
              {alerts.map((alert) => (
                <button key={alert.id} type="button" className={`hd-alert-row ${alert.tone}`} onClick={() => navigate(alert.route)}>
                  <AlertTriangle size={18} strokeWidth={1.8} />
                  <div>
                    <strong>{alert.title}</strong>
                    <span>{alert.description}</span>
                  </div>
                  <ArrowRight size={16} strokeWidth={1.8} />
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Inventario">
          <div className="hd-inventory-card">
            <Boxes size={24} strokeWidth={1.8} />
            <div>
              <strong>{lowStockCount}</strong>
              <span>productos bajo stock</span>
            </div>
            <button type="button" onClick={() => navigate('/productsList')}>Ver inventario</button>
          </div>
        </Panel>
      </section>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, caption }) {
  return (
    <article className="hd-metric-card">
      <span className="hd-metric-icon"><Icon size={19} strokeWidth={1.8} /></span>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <small>{caption}</small>
      </div>
    </article>
  );
}

function Panel({ title, actionLabel, onAction, children }) {
  return (
    <article className="hd-panel">
      <header>
        <h2>{title}</h2>
        {actionLabel && (
          <button type="button" onClick={onAction}>
            {actionLabel}
            <ArrowRight size={14} strokeWidth={1.8} />
          </button>
        )}
      </header>
      {children}
    </article>
  );
}

function EmptyState({ text }) {
  return (
    <div className="hd-empty-state">
      <RefreshCw size={18} strokeWidth={1.8} />
      <span>{text}</span>
    </div>
  );
}

function FiscalPill({ label, value, tone }) {
  return (
    <div className={`hd-fiscal-pill ${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function ReadinessItem({ icon: Icon, label, value, tone }) {
  return (
    <div className={`hd-readiness-item ${tone}`}>
      <Icon size={17} strokeWidth={1.8} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function getCertificateSummary(issuers) {
  if (!issuers.length) {
    return {
      tone: 'danger',
      shortLabel: 'Sin emisor',
      title: 'Sin emisor fiscal configurado',
      description: 'Configura un emisor DGII para operar e-CF.',
    };
  }

  const statuses = issuers.map((issuer) => issuer.certificate_status || 'missing');
  if (statuses.includes('active')) {
    return {
      tone: 'success',
      shortLabel: 'Activo',
      title: 'Certificado DGII activo',
      description: 'Hay al menos un emisor con certificado activo.',
    };
  }
  if (statuses.includes('expiring_soon')) {
    return {
      tone: 'warning',
      shortLabel: 'Por vencer',
      title: 'Certificado DGII próximo a vencer',
      description: 'Revisa la vigencia del certificado en Empresa.',
    };
  }
  if (statuses.includes('expired')) {
    return {
      tone: 'danger',
      shortLabel: 'Vencido',
      title: 'Certificado DGII vencido',
      description: 'Renueva el certificado antes de firmar e-CF.',
    };
  }
  if (statuses.includes('invalid')) {
    return {
      tone: 'danger',
      shortLabel: 'Inválido',
      title: 'Certificado DGII inválido',
      description: 'Revisa el archivo o la contraseña del certificado.',
    };
  }
  return {
    tone: 'warning',
    shortLabel: 'Faltante',
    title: 'Certificado DGII faltante',
    description: 'Carga un certificado DGII para habilitar firma real.',
  };
}

function getMissingSequenceTypes(sequences) {
  const labels = { 31: 'E31', 32: 'E32', 34: 'E34' };
  return ['31', '32', '34'].filter((type) => (
    !sequences.some((sequence) => normalizeEcfType(sequence.ecf_type) === type && sequence.is_active)
  )).map((type) => labels[type]);
}

function normalizeEcfType(value) {
  return String(value || '').replace(/^E/i, '');
}

export default Home;
