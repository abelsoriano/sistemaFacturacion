import React, { useState, useEffect, useMemo } from 'react';
import api from '../services/api';
import { showErrorAlert } from '../herpert';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import { FINANCIAL_TOTALS_PERMISSIONS, userHasAnyPermission } from '../utils/permissions';
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
  IconChevLeft,
  IconChevRight,
  IconReceipt,
} from './Icons';



const ROWS_PER_PAGE = 10;
const invoiceDate = (invoice) => invoice.created_at || invoice.date;
const invoiceCustomer = (invoice) => invoice.client_name || invoice.customer || 'Consumidor Final';
const invoiceNumber = (invoice) => invoice.invoice_number || `FAC-${invoice.id}`;
const isPaidInvoice = (invoice) => invoice.status === 'paid';
const isPendingInvoice = (invoice) => invoice.status === 'pending';

const SalesList = () => {
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const canViewSalesTotals = userHasAnyPermission(currentUser, FINANCIAL_TOTALS_PERMISSIONS);
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
      const res = await api.get('/invoices/');
      setSales(res.data);
    } catch (err) {
      setError('Error al cargar las ventas desde facturas. Por favor, intente nuevamente.');
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
        const customer = invoiceCustomer(s).toLowerCase();
        const date = new Date(invoiceDate(s)).toLocaleString().toLowerCase();
        const number = invoiceNumber(s).toLowerCase();
        return customer.includes(q) || date.includes(q) || number.includes(q);
      });
    }
    if (dateRange.start && dateRange.end) {
      const start = normalizeDate(dateRange.start);
      const end   = normalizeDate(dateRange.end);
      result = result.filter(s => {
        const d = normalizeDate(invoiceDate(s));
        return d && d >= start && d <= end;
      });
    }
    return result;
  }, [sales, search, dateRange]);

  // Stats derivados
  const statsData = useMemo(() => {
    const paidInvoices = sales.filter(isPaidInvoice);
    const pendingInvoices = sales.filter(isPendingInvoice);
    const total    = paidInvoices.length;
    const ingresos = paidInvoices.reduce((acc, s) => acc + (parseFloat(s.total) || 0), 0);
    const porCobrar = pendingInvoices.reduce((acc, s) => acc + (parseFloat(s.total) || 0), 0);
    const today    = new Date().toISOString().split('T')[0];
    const hoy      = paidInvoices.filter(s => invoiceDate(s)?.startsWith(today)).length;
    const ticket   = total > 0 ? ingresos / total : 0;
    return { total, ingresos, hoy, ticket, pendientes: pendingInvoices.length, porCobrar };
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

  const exportToExcel = () => {
    if (filteredSales.length === 0) { showErrorAlert('Error', 'No hay datos para exportar.'); return; }
    try {
      const ws = XLSX.utils.json_to_sheet(filteredSales.map(s => ({
        'Factura':          invoiceNumber(s),
        'Cliente':          invoiceCustomer(s),
        'Fecha':            new Date(invoiceDate(s)).toLocaleString(),
        ...(canViewSalesTotals ? { 'Total': `$${parseFloat(s.total || 0).toFixed(2)}` } : {}),
        'Productos':        s.details?.length || 0,
        'Estado':           s.status || '',
        'e-CF':             s.ecf_status || '',
      })));
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Facturas');
      XLSX.writeFile(wb, `facturas_${new Date().toISOString().slice(0, 10)}.xlsx`);
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
          clientName: invoiceCustomer(drawerSale),
          date: invoiceDate(drawerSale),
          total: drawerSale.total,
          invoice_number: invoiceNumber(drawerSale),
        },
        {
          filename: `factura_${invoiceNumber(drawerSale)}.pdf`,
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
  const drawerTax   = drawerSubtotal * 0.18;
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
          <button className="sl-btn sl-btn-primary" onClick={() => navigate('/Fastsales')}>
            <IconPlus /> Nueva venta
          </button>
        </nav>

        <div className="sl-body">

          {/* Stats */}
          <div className="sl-stats">
            {canViewSalesTotals && (
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ventas cobradas</div>
              <div className="sl-stat-val">{isLoading ? '—' : statsData.total}</div>
            </div>
            )}
            {canViewSalesTotals && (
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ingresos cobrados</div>
              <div className="sl-stat-val">{isLoading ? '—' : `$${fmt(statsData.ingresos)}`}</div>
            </div>
            )}
            <div className="sl-stat">
              <div className="sl-stat-lbl">Ventas cobradas hoy</div>
              <div className="sl-stat-val">{isLoading ? '—' : statsData.hoy}</div>
            </div>
            <div className="sl-stat">
              <div className="sl-stat-lbl">Cuentas por cobrar</div>
              <div className="sl-stat-val">{isLoading ? '—' : statsData.pendientes}</div>
              {canViewSalesTotals && (
                <div className="sl-stat-sub">{isLoading ? '—' : `$${fmt(statsData.porCobrar)}`} pendiente de cobro</div>
              )}
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
                Cargando facturas...
              </div>
            ) : paginated.length === 0 ? (
              <div className="sl-empty">
                <div className="sl-empty-icon"><IconReceipt /></div>
                <p>{search || dateRange.start ? 'No hay facturas con los filtros aplicados.' : 'No hay facturas registradas.'}</p>
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
                        <td data-label="Factura" className="muted mono" style={{ fontSize: 12 }}>{invoiceNumber(sale)}</td>
                        <td data-label="Cliente" style={{ fontWeight: 500 }}>{invoiceCustomer(sale)}</td>
                        <td data-label="Fecha" className="muted" style={{ fontSize: 12 }}>
                          {new Date(invoiceDate(sale)).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })}
                          {' '}
                          <span style={{ color: '#d1d5db' }}>
                            {new Date(invoiceDate(sale)).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </td>
                        {canViewSalesTotals && <td data-label="Total" className="r mono" style={{ fontWeight: 600, color: '#0F6E56' }}>
                          ${fmt(parseFloat(sale.total || 0))}
                        </td>}
                        <td data-label="Productos" className="c">
                          <span className="sl-badge">{sale.details?.length || 0}</span>
                        </td>
                        <td data-label="Acciones" className="c">
                          <div style={{ display: 'flex', gap: 5, justifyContent: 'center' }}>
                            <button
                              className="sl-act-btn sl-act-view"
                              title="Ver detalles"
                              onClick={() => setDrawerSale(sale)}
                            >
                              <IconEye />
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
                    {filteredSales.length === 0 ? '0' : `${(currentPage - 1) * ROWS_PER_PAGE + 1}–${Math.min(currentPage * ROWS_PER_PAGE, filteredSales.length)}`} de {filteredSales.length} facturas
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
                <span className="sl-drawer-title">Detalle de factura {invoiceNumber(drawerSale)}</span>

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
                  <span>{invoiceCustomer(drawerSale)}</span>
                </div>
                <div className="sl-drawer-meta-row">
                  <span>Fecha</span>
                  <span>{new Date(invoiceDate(drawerSale)).toLocaleString('es-MX')}</span>
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
                  <span className="lbl">ITBIS 18%</span>
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
