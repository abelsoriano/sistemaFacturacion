import React, { useState, useEffect, useMemo } from 'react';
import api from '../services/api';
import Swal from 'sweetalert2';
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from '../herpert';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import { SALE_TOTALS_PERMISSION, userHasPermissions } from '../utils/permissions';
import { Printer } from 'lucide-react';
import { generatePDF } from './generatePDF';
import '../css/SalesList.css';
import {
  IconArrowLeft,
  IconSearch,
  IconX,
  IconPlus,
  IconExcel,
  IconEye,
  IconEdit,
  IconTrash,
  IconChevLeft,
  IconChevRight,
  IconReceipt,
} from './Icons';



const ROWS_PER_PAGE = 10;

const SalesList = () => {
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const canViewSalesTotals = userHasPermissions(currentUser, [SALE_TOTALS_PERMISSION]);
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
        ...(canViewSalesTotals ? { 'Total': `$${parseFloat(s.total || 0).toFixed(2)}` } : {}),
        'Productos':        s.details?.length || 0,
      })));
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Ventas');
      XLSX.writeFile(wb, `ventas_${new Date().toISOString().slice(0, 10)}.xlsx`);
    } catch (err) {
      showErrorAlert('Error', 'No se pudo generar el archivo Excel.');
    }
  };

  const handlePrintSale = () => {
    if (!drawerSale) return;
    try {
      generatePDF(
        {
          items: drawerSale.details || [],
          clientName: drawerSale.customer || 'Consumidor Final',
          date: drawerSale.date,
          total: drawerSale.total,
          invoice_number: drawerSale.id,
        },
        {
          filename: `venta_${drawerSale.id || 'ticket'}.pdf`,
          showClientName: true,
        }
      );
    } catch (err) {
      showErrorAlert('Error', 'No se pudo generar el PDF.');
      console.error(err);
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
            {canViewSalesTotals && (
            <div className="sl-stat">
              <div className="sl-stat-lbl">Total ventas</div>
              <div className="sl-stat-val">{isLoading ? '—' : statsData.total}</div>
            </div>
            )}
            {canViewSalesTotals && (
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ingresos totales</div>
              <div className="sl-stat-val">{isLoading ? '—' : `$${fmt(statsData.ingresos)}`}</div>
            </div>
            )}
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ventas hoy</div>
              <div className="sl-stat-val">{isLoading ? '—' : statsData.hoy}</div>
            </div>
            {canViewSalesTotals && (
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ticket promedio</div>
              <div className="sl-stat-val">{isLoading ? '—' : `$${fmt(statsData.ticket)}`}</div>
            </div>
            )}
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
                      {canViewSalesTotals && <th className="r" style={{ width: 120 }}>Total</th>}
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
                        {canViewSalesTotals && <td className="r mono" style={{ fontWeight: 600, color: '#0F6E56' }}>
                          ${fmt(parseFloat(sale.total || 0))}
                        </td>}
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
                              onClick={() => navigate(`/Fastsales/${sale.id}`)}
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

                <button className="sl-drawer-close" onClick={handlePrintSale} title="Imprimir PDF">
                  <Printer />
                </button>

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
                        {canViewSalesTotals && (
                          <>
                            <div className="sl-detail-sub">${fmt(parseFloat(item.subtotal || 0))}</div>
                            <div className="sl-detail-price">${fmt(parseFloat(item.price || 0))} c/u</div>
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {canViewSalesTotals && (
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
              )}

            </div>
          </div>
        )}

      </div>
    </>
  );
};

export default SalesList;
