import React, { useState, useEffect, useMemo } from 'react';
import api from '../services/api';
import Swal from 'sweetalert2';
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from '../herpert';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';

const styles = `
  .sl-shell { background: #f4f5f7; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

  .sl-nav {
    background: #fff; border-bottom: 0.5px solid #e5e7eb;
    padding: 0 24px; height: 56px;
    display: flex; align-items: center; gap: 12px;
    position: sticky; top: 0; z-index: 100;
  }
  .sl-nav-back {
    display: flex; align-items: center; gap: 5px;
    font-size: 12px; color: #6b7280;
    background: transparent; border: 0.5px solid #e5e7eb;
    border-radius: 8px; padding: 5px 12px; cursor: pointer;
    transition: background 0.15s;
  }
  .sl-nav-back:hover { background: #f9fafb; }
  .sl-nav-title { font-size: 15px; font-weight: 600; color: #111827; flex: 1; }
  .sl-btn {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 500;
    border-radius: 8px; padding: 6px 14px;
    cursor: pointer; transition: all 0.15s;
  }
  .sl-btn-ghost {
    background: transparent; color: #6b7280;
    border: 0.5px solid #e5e7eb;
  }
  .sl-btn-ghost:hover { background: #f9fafb; color: #111827; }
  .sl-btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }
  .sl-btn-primary {
    background: #1D9E75; color: #fff; border: none;
  }
  .sl-btn-primary:hover { background: #0F6E56; }

  .sl-body { max-width: 1100px; margin: 0 auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }

  .sl-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
  .sl-stat {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; padding: 14px 16px;
  }
  .sl-stat-lbl { font-size: 10px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
  .sl-stat-val { font-size: 22px; font-weight: 600; color: #111827; }

  .sl-filters {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; padding: 12px 16px;
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  }
  .sl-search {
    display: flex; align-items: center; gap: 7px;
    background: #f9fafb; border: 0.5px solid #e5e7eb;
    border-radius: 8px; padding: 7px 12px; flex: 1; min-width: 200px;
    transition: border-color 0.15s;
  }
  .sl-search:focus-within { border-color: #1D9E75; background: #fff; }
  .sl-search input {
    border: none; background: transparent;
    font-size: 13px; color: #111827; outline: none; width: 100%;
  }
  .sl-date-input {
    background: #f9fafb; border: 0.5px solid #e5e7eb;
    border-radius: 8px; padding: 7px 10px;
    font-size: 12px; color: #374151; outline: none;
    transition: border-color 0.15s;
  }
  .sl-date-input:focus { border-color: #1D9E75; }

  .sl-table-card {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; overflow: hidden;
  }
  .sl-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .sl-table thead th {
    padding: 9px 16px;
    text-align: left;
    font-size: 10px; font-weight: 600; color: #9ca3af;
    background: #f9fafb; border-bottom: 0.5px solid #f3f4f6;
    text-transform: uppercase; letter-spacing: 0.05em;
    white-space: nowrap;
  }
  .sl-table thead th.r { text-align: right; }
  .sl-table thead th.c { text-align: center; }
  .sl-table tbody tr { border-bottom: 0.5px solid #f9fafb; transition: background 0.1s; }
  .sl-table tbody tr:last-child { border-bottom: none; }
  .sl-table tbody tr:hover { background: #f9fafb; }
  .sl-table tbody td { padding: 11px 16px; vertical-align: middle; color: #111827; }
  .sl-table tbody td.muted { color: #9ca3af; }
  .sl-table tbody td.r { text-align: right; }
  .sl-table tbody td.c { text-align: center; }
  .sl-table tbody td.mono { font-variant-numeric: tabular-nums; }
  .sl-badge {
    display: inline-block;
    background: #E1F5EE; color: #085041;
    font-size: 10px; font-weight: 500;
    padding: 2px 9px; border-radius: 10px;
  }
  .sl-act-btn {
    width: 28px; height: 28px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 6px; border: 0.5px solid transparent;
    background: transparent; cursor: pointer;
    transition: all 0.1s; flex-shrink: 0;
  }
  .sl-act-view  { color: #185FA5; background: #E6F1FB; border-color: #B5D4F4; }
  .sl-act-edit  { color: #854F0B; background: #FAEEDA; border-color: #FAC775; }
  .sl-act-del   { color: #A32D2D; background: #FCEBEB; border-color: #F7C1C1; }
  .sl-act-view:hover { background: #B5D4F4; }
  .sl-act-edit:hover { background: #FAC775; }
  .sl-act-del:hover  { background: #F7C1C1; }

  .sl-pagination {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 16px; border-top: 0.5px solid #f3f4f6;
    font-size: 12px; color: #6b7280;
  }
  .sl-pg-btns { display: flex; gap: 4px; }
  .sl-pg-btn {
    min-width: 28px; height: 28px; padding: 0 6px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 6px; border: 0.5px solid #e5e7eb;
    background: transparent; cursor: pointer;
    font-size: 12px; color: #6b7280; transition: all 0.1s;
  }
  .sl-pg-btn:hover:not(:disabled) { background: #f3f4f6; color: #111827; }
  .sl-pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .sl-pg-btn.active { background: #1D9E75; color: #fff; border-color: #1D9E75; }

  .sl-empty { padding: 48px; text-align: center; color: #9ca3af; }
  .sl-empty-icon { font-size: 40px; opacity: 0.25; margin-bottom: 12px; }
  .sl-empty p { font-size: 14px; }
  .sl-empty small { font-size: 12px; color: #d1d5db; }

  .sl-loading { padding: 48px; text-align: center; color: #9ca3af; font-size: 13px; }
  .sl-spinner {
    width: 24px; height: 24px; border: 2px solid #e5e7eb;
    border-top-color: #1D9E75; border-radius: 50%;
    animation: sl-spin 0.6s linear infinite; margin: 0 auto 12px;
  }
  @keyframes sl-spin { to { transform: rotate(360deg); } }

  .sl-error {
    background: #FCEBEB; border: 0.5px solid #F7C1C1;
    border-radius: 10px; padding: 14px 16px;
    display: flex; align-items: center; justify-content: space-between;
    font-size: 13px; color: #A32D2D;
  }

  /* Drawer de detalles */
  .sl-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 200;
    display: flex; justify-content: flex-end;
  }
  .sl-drawer {
    background: #fff; width: 420px; max-width: 90vw;
    height: 100vh; display: flex; flex-direction: column;
    box-shadow: -4px 0 24px rgba(0,0,0,0.08);
  }
  .sl-drawer-header {
    padding: 16px 20px; border-bottom: 0.5px solid #f3f4f6;
    display: flex; align-items: center; gap: 10px; flex-shrink: 0;
  }
  .sl-drawer-title { font-size: 14px; font-weight: 600; color: #111827; flex: 1; }
  .sl-drawer-close {
    width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
    border-radius: 6px; border: 0.5px solid #e5e7eb; background: transparent; cursor: pointer;
    color: #6b7280;
  }
  .sl-drawer-close:hover { background: #f9fafb; }
  .sl-drawer-meta {
    padding: 14px 20px; border-bottom: 0.5px solid #f3f4f6;
    display: flex; flex-direction: column; gap: 6px; flex-shrink: 0;
  }
  .sl-drawer-meta-row {
    display: flex; justify-content: space-between; font-size: 12px;
  }
  .sl-drawer-meta-row span:first-child { color: #9ca3af; }
  .sl-drawer-meta-row span:last-child { color: #111827; font-weight: 500; }
  .sl-drawer-items { flex: 1; overflow-y: auto; padding: 14px 20px; display: flex; flex-direction: column; gap: 8px; }
  .sl-detail-item {
    background: #f9fafb; border: 0.5px solid #f3f4f6;
    border-radius: 8px; padding: 10px 12px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .sl-detail-name { font-size: 13px; font-weight: 500; color: #111827; }
  .sl-detail-qty { font-size: 11px; color: #9ca3af; margin-top: 2px; }
  .sl-detail-sub { font-size: 13px; font-weight: 600; color: #111827; }
  .sl-detail-price { font-size: 11px; color: #9ca3af; text-align: right; margin-top: 2px; }
  .sl-drawer-footer {
    padding: 14px 20px; border-top: 0.5px solid #f3f4f6; flex-shrink: 0;
  }
  .sl-drawer-total-row {
    display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 3px 0;
  }
  .sl-drawer-total-row .lbl { color: #9ca3af; }
  .sl-drawer-total-row .val { font-weight: 500; color: #111827; }
  .sl-drawer-grand {
    display: flex; justify-content: space-between; align-items: center;
    padding-top: 10px; margin-top: 6px; border-top: 0.5px solid #f3f4f6;
  }
  .sl-drawer-grand .lbl { font-size: 14px; font-weight: 600; color: #111827; }
  .sl-drawer-grand .val { font-size: 20px; font-weight: 700; color: #0F6E56; }

  @media (max-width: 768px) {
    .sl-stats { grid-template-columns: repeat(2,1fr); }
    .sl-nav-title { display: none; }
    .sl-drawer { width: 100vw; }
  }
`;

// Iconos SVG inline
const IconArrowLeft = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
  </svg>
);
const IconSearch = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);
const IconX = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" viewBox="0 0 24 24">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconPlus = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" viewBox="0 0 24 24">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);
const IconExcel = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/>
  </svg>
);
const IconEye = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
);
const IconEdit = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
);
const IconTrash = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>
    <path d="M9 6V4h6v2"/>
  </svg>
);
const IconChevLeft = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="15 18 9 12 15 6"/>
  </svg>
);
const IconChevRight = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="9 18 15 12 9 6"/>
  </svg>
);
const IconReceipt = () => (
  <svg width="16" height="16" fill="none" stroke="#1D9E75" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1z"/>
    <line x1="9" y1="7" x2="15" y2="7"/><line x1="9" y1="11" x2="15" y2="11"/>
  </svg>
);

const ROWS_PER_PAGE = 10;

const SalesList = () => {
  const [sales, setSales]                     = useState([]);
  const [isLoading, setIsLoading]             = useState(false);
  const [error, setError]                     = useState(null);
  const [search, setSearch]                   = useState('');
  const [dateRange, setDateRange]             = useState({ start: '', end: '' });
  const [page, setPage]                       = useState(1);
  const [drawerSale, setDrawerSale]           = useState(null);
  const navigate = useNavigate();

  const normalizeDate = (d) => {
    if (!d) return null;
    const dt = new Date(d);
    return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
  };

  const fetchSales = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get('/sales/list/');
      setSales(res.data);
    } catch (err) {
      setError('Error al cargar las ventas. Por favor, intente nuevamente.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchSales(); }, []);

  // Filtrado
  const filteredSales = useMemo(() => {
    let result = [...sales];
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(s => {
        const customer = (s.customer || '').toLowerCase();
        const date = new Date(s.date).toLocaleString().toLowerCase();
        return customer.includes(q) || date.includes(q);
      });
    }
    if (dateRange.start && dateRange.end) {
      const start = normalizeDate(dateRange.start);
      const end   = normalizeDate(dateRange.end);
      result = result.filter(s => {
        const d = normalizeDate(s.date);
        return d && d >= start && d <= end;
      });
    }
    return result;
  }, [sales, search, dateRange]);

  // Stats derivados
  const statsData = useMemo(() => {
    const total    = sales.length;
    const ingresos = sales.reduce((acc, s) => acc + (parseFloat(s.total) || 0), 0);
    const today    = new Date().toISOString().split('T')[0];
    const hoy      = sales.filter(s => s.date?.startsWith(today)).length;
    const ticket   = total > 0 ? ingresos / total : 0;
    return { total, ingresos, hoy, ticket };
  }, [sales]);

  // Paginación
  const totalPages   = Math.max(1, Math.ceil(filteredSales.length / ROWS_PER_PAGE));
  const currentPage  = Math.min(page, totalPages);
  const paginated    = filteredSales.slice((currentPage - 1) * ROWS_PER_PAGE, currentPage * ROWS_PER_PAGE);

  const getPageNums = () => {
    const pages = [];
    const start = Math.max(1, currentPage - 1);
    const end   = Math.min(totalPages, start + 2);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  };

  const clearFilters = () => {
    setSearch('');
    setDateRange({ start: '', end: '' });
    setPage(1);
  };

  const handleDelete = async (id) => {
    const result = await showConfirmationAlert('¿Estás seguro?', 'Esta acción no se puede deshacer.');
    if (result.isConfirmed) {
      try {
        await api.delete(`/salesUpdate/${id}/`);
        setSales(prev => prev.filter(s => s.id !== id));
        if (drawerSale?.id === id) setDrawerSale(null);
        showSuccessAlert('Eliminado', 'La venta ha sido eliminada correctamente.');
      } catch (err) {
        showErrorAlert('Error', 'No se pudo eliminar la venta.');
      }
    }
  };

  const exportToExcel = () => {
    if (filteredSales.length === 0) { showErrorAlert('Error', 'No hay datos para exportar.'); return; }
    try {
      const ws = XLSX.utils.json_to_sheet(filteredSales.map(s => ({
        'ID':               s.id,
        'Cliente':          s.customer || 'N/A',
        'Fecha':            new Date(s.date).toLocaleString(),
        'Total':            `$${parseFloat(s.total || 0).toFixed(2)}`,
        'Productos':        s.details?.length || 0,
      })));
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Ventas');
      XLSX.writeFile(wb, `ventas_${new Date().toISOString().slice(0, 10)}.xlsx`);
    } catch (err) {
      showErrorAlert('Error', 'No se pudo generar el archivo Excel.');
    }
  };

  // Cálculos del drawer
  const drawerSubtotal = drawerSale
    ? drawerSale.details.reduce((a, i) => a + (parseFloat(i.subtotal) || 0), 0)
    : 0;
  const drawerTax   = drawerSubtotal * 0.16;
  const drawerTotal = drawerSubtotal + drawerTax;

  const fmt = (n) => new Intl.NumberFormat('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);

  return (
    <>
      <style>{styles}</style>
      <div className="sl-shell">

        {/* Navbar */}
        <nav className="sl-nav">
          <button className="sl-nav-back sl-btn" onClick={() => navigate('/home')}>
            <IconArrowLeft /> Volver
          </button>
          <span className="sl-nav-title">Ventas</span>
          <button
            className="sl-btn sl-btn-ghost"
            onClick={exportToExcel}
            disabled={filteredSales.length === 0}
          >
            <IconExcel /> Exportar Excel
          </button>
          <button className="sl-btn sl-btn-primary" onClick={() => navigate('/sales')}>
            <IconPlus /> Nueva venta
          </button>
        </nav>

        <div className="sl-body">

          {/* Stats */}
          <div className="sl-stats">
            <div className="sl-stat">
              <div className="sl-stat-lbl">Total ventas</div>
              <div className="sl-stat-val">{isLoading ? '—' : statsData.total}</div>
            </div>
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ingresos totales</div>
              <div className="sl-stat-val">{isLoading ? '—' : `$${fmt(statsData.ingresos)}`}</div>
            </div>
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ventas hoy</div>
              <div className="sl-stat-val">{isLoading ? '—' : statsData.hoy}</div>
            </div>
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ticket promedio</div>
              <div className="sl-stat-val">{isLoading ? '—' : `$${fmt(statsData.ticket)}`}</div>
            </div>
          </div>

          {/* Filtros */}
          <div className="sl-filters">
            <div className="sl-search">
              <IconSearch />
              <input
                type="text"
                placeholder="Buscar por cliente o fecha..."
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1); }}
              />
              {search && (
                <button
                  onClick={() => { setSearch(''); setPage(1); }}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: 0, display: 'flex' }}
                >
                  <IconX />
                </button>
              )}
            </div>
            <input
              type="date"
              className="sl-date-input"
              value={dateRange.start}
              onChange={e => { setDateRange(p => ({ ...p, start: e.target.value })); setPage(1); }}
            />
            <input
              type="date"
              className="sl-date-input"
              value={dateRange.end}
              min={dateRange.start}
              onChange={e => { setDateRange(p => ({ ...p, end: e.target.value })); setPage(1); }}
            />
            <button
              className="sl-btn sl-btn-ghost"
              onClick={clearFilters}
              disabled={!search && !dateRange.start && !dateRange.end}
            >
              <IconX /> Limpiar
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="sl-error">
              <span>{error}</span>
              <button className="sl-btn sl-btn-ghost" onClick={fetchSales}>Reintentar</button>
            </div>
          )}

          {/* Tabla */}
          <div className="sl-table-card">
            {isLoading ? (
              <div className="sl-loading">
                <div className="sl-spinner" />
                Cargando ventas...
              </div>
            ) : paginated.length === 0 ? (
              <div className="sl-empty">
                <div className="sl-empty-icon">🧾</div>
                <p>{search || dateRange.start ? 'No hay ventas con los filtros aplicados.' : 'No hay ventas registradas.'}</p>
                <small>Crea una nueva venta desde el botón superior</small>
              </div>
            ) : (
              <>
                <table className="sl-table">
                  <thead>
                    <tr>
                      <th style={{ width: 64 }}>#</th>
                      <th>Cliente</th>
                      <th style={{ width: 170 }}>Fecha</th>
                      <th className="r" style={{ width: 120 }}>Total</th>
                      <th className="c" style={{ width: 100 }}>Productos</th>
                      <th className="c" style={{ width: 120 }}>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.map(sale => (
                      <tr key={sale.id}>
                        <td className="muted mono" style={{ fontSize: 12 }}>#{sale.id}</td>
                        <td style={{ fontWeight: 500 }}>{sale.customer || 'Consumidor Final'}</td>
                        <td className="muted" style={{ fontSize: 12 }}>
                          {new Date(sale.date).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })}
                          {' '}
                          <span style={{ color: '#d1d5db' }}>
                            {new Date(sale.date).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </td>
                        <td className="r mono" style={{ fontWeight: 600, color: '#0F6E56' }}>
                          ${fmt(parseFloat(sale.total || 0))}
                        </td>
                        <td className="c">
                          <span className="sl-badge">{sale.details?.length || 0}</span>
                        </td>
                        <td className="c">
                          <div style={{ display: 'flex', gap: 5, justifyContent: 'center' }}>
                            <button
                              className="sl-act-btn sl-act-view"
                              title="Ver detalles"
                              onClick={() => setDrawerSale(sale)}
                            >
                              <IconEye />
                            </button>
                            <button
                              className="sl-act-btn sl-act-edit"
                              title="Editar"
                              onClick={() => navigate(`/SalesForm/${sale.id}`)}
                            >
                              <IconEdit />
                            </button>
                            <button
                              className="sl-act-btn sl-act-del"
                              title="Eliminar"
                              onClick={() => handleDelete(sale.id)}
                            >
                              <IconTrash />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Paginación */}
                <div className="sl-pagination">
                  <span>
                    {filteredSales.length === 0 ? '0' : `${(currentPage - 1) * ROWS_PER_PAGE + 1}–${Math.min(currentPage * ROWS_PER_PAGE, filteredSales.length)}`} de {filteredSales.length} ventas
                  </span>
                  <div className="sl-pg-btns">
                    <button className="sl-pg-btn" onClick={() => setPage(p => p - 1)} disabled={currentPage === 1}>
                      <IconChevLeft />
                    </button>
                    {getPageNums().map(n => (
                      <button
                        key={n}
                        className={`sl-pg-btn${n === currentPage ? ' active' : ''}`}
                        onClick={() => setPage(n)}
                      >
                        {n}
                      </button>
                    ))}
                    <button className="sl-pg-btn" onClick={() => setPage(p => p + 1)} disabled={currentPage === totalPages}>
                      <IconChevRight />
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Drawer de detalles */}
        {drawerSale && (
          <div className="sl-overlay" onClick={() => setDrawerSale(null)}>
            <div className="sl-drawer" onClick={e => e.stopPropagation()}>

              <div className="sl-drawer-header">
                <IconReceipt />
                <span className="sl-drawer-title">Detalles de venta #{drawerSale.id}</span>
                <button className="sl-drawer-close" onClick={() => setDrawerSale(null)}>
                  <IconX />
                </button>
              </div>

              <div className="sl-drawer-meta">
                <div className="sl-drawer-meta-row">
                  <span>Cliente</span>
                  <span>{drawerSale.customer || 'Consumidor Final'}</span>
                </div>
                <div className="sl-drawer-meta-row">
                  <span>Fecha</span>
                  <span>{new Date(drawerSale.date).toLocaleString('es-MX')}</span>
                </div>
                <div className="sl-drawer-meta-row">
                  <span>Productos</span>
                  <span>{drawerSale.details?.length || 0} artículos</span>
                </div>
              </div>

              <div className="sl-drawer-items">
                {(!drawerSale.details || drawerSale.details.length === 0) ? (
                  <div style={{ textAlign: 'center', color: '#9ca3af', padding: '32px 0', fontSize: 13 }}>
                    No hay detalles disponibles
                  </div>
                ) : (
                  drawerSale.details.map((item, i) => (
                    <div key={i} className="sl-detail-item">
                      <div>
                        <div className="sl-detail-name">{item.product_name || 'N/A'}</div>
                        <div className="sl-detail-qty">Cantidad: {item.quantity}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div className="sl-detail-sub">${fmt(parseFloat(item.subtotal || 0))}</div>
                        <div className="sl-detail-price">${fmt(parseFloat(item.price || 0))} c/u</div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="sl-drawer-footer">
                <div className="sl-drawer-total-row">
                  <span className="lbl">Subtotal</span>
                  <span className="val">${fmt(drawerSubtotal)}</span>
                </div>
                <div className="sl-drawer-total-row">
                  <span className="lbl">IVA 16%</span>
                  <span className="val">${fmt(drawerTax)}</span>
                </div>
                <div className="sl-drawer-grand">
                  <span className="lbl">Total</span>
                  <span className="val">${fmt(drawerTotal)}</span>
                </div>
              </div>

            </div>
          </div>
        )}

      </div>
    </>
  );
};

export default SalesList;