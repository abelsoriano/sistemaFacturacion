import React, { useState } from 'react';
import api from '../services/api';

const styles = `
  .pdf-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.35);
    z-index: 300;
    display: flex; align-items: center; justify-content: center;
    padding: 24px;
  }
  .pdf-modal {
    background: #fff;
    border-radius: 12px;
    border: 0.5px solid #e5e7eb;
    width: 100%; max-width: 820px;
    max-height: 90vh;
    display: flex; flex-direction: column;
    overflow: hidden;
  }
  .pdf-header {
    padding: 16px 20px;
    border-bottom: 0.5px solid #f3f4f6;
    display: flex; align-items: flex-start; gap: 12px;
    flex-shrink: 0;
  }
  .pdf-header-icon {
    width: 36px; height: 36px; border-radius: 8px;
    background: #FCEBEB; display: flex; align-items: center;
    justify-content: center; flex-shrink: 0;
  }
  .pdf-header-info { flex: 1; }
  .pdf-header-title { font-size: 14px; font-weight: 600; color: #111827; }
  .pdf-header-desc  { font-size: 12px; color: #9ca3af; margin-top: 2px; }
  .pdf-close {
    width: 28px; height: 28px; border-radius: 6px;
    border: 0.5px solid #e5e7eb; background: transparent;
    cursor: pointer; color: #6b7280;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.12s; flex-shrink: 0;
  }
  .pdf-close:hover { background: #f9fafb; }
  .pdf-close:disabled { opacity: 0.4; cursor: not-allowed; }

  .pdf-body {
    flex: 1; overflow-y: auto; padding: 20px;
    display: flex; flex-direction: column; gap: 16px;
  }

  .pdf-error {
    background: #FCEBEB; border: 0.5px solid #F7C1C1;
    border-radius: 8px; padding: 12px 14px;
    font-size: 13px; color: #A32D2D;
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
  }
  .pdf-error-close {
    background: none; border: none; cursor: pointer;
    color: #A32D2D; padding: 0; display: flex;
  }

  .pdf-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .pdf-stat {
    background: #f9fafb; border-radius: 8px;
    padding: 12px 14px; text-align: center;
  }
  .pdf-stat-val { font-size: 22px; font-weight: 600; color: #111827; }
  .pdf-stat-lbl { font-size: 11px; color: #9ca3af; margin-top: 2px; }

  .pdf-alert {
    display: flex; align-items: flex-start; gap: 10px;
    border-radius: 8px; padding: 12px 14px; font-size: 13px;
  }
  .pdf-alert.warn {
    background: #FAEEDA; border: 0.5px solid #FAC775; color: #633806;
  }
  .pdf-alert.danger {
    background: #FCEBEB; border: 0.5px solid #F7C1C1; color: #791F1F;
  }
  .pdf-alert.success {
    background: #E1F5EE; border: 0.5px solid #5DCAA5; color: #085041;
  }
  .pdf-alert-title { font-weight: 600; margin-bottom: 3px; }

  .pdf-table-wrap { overflow-x: auto; }
  .pdf-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .pdf-table thead th {
    padding: 8px 12px; text-align: left;
    font-size: 10px; font-weight: 600; color: #9ca3af;
    background: #f9fafb; border-bottom: 0.5px solid #f3f4f6;
    text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;
  }
  .pdf-table thead th.c { text-align: center; }
  .pdf-table tbody tr { border-bottom: 0.5px solid #f9fafb; }
  .pdf-table tbody tr:last-child { border-bottom: none; }
  .pdf-table tbody tr:hover { background: #f9fafb; }
  .pdf-table tbody td { padding: 10px 12px; vertical-align: middle; color: #111827; }
  .pdf-table tbody td.c { text-align: center; }
  .pdf-table tbody td.muted { color: #9ca3af; font-size: 11px; }

  .pdf-badge {
    display: inline-block; font-size: 10px; font-weight: 500;
    padding: 2px 8px; border-radius: 10px;
  }
  .pdf-badge-out      { background: #FCEBEB; color: #A32D2D; }
  .pdf-badge-critical { background: #FAEEDA; color: #854F0B; }
  .pdf-badge-low      { background: #E6F1FB; color: #185FA5; }
  .pdf-badge-hi       { background: #FCEBEB; color: #A32D2D; }
  .pdf-badge-med      { background: #FAEEDA; color: #854F0B; }
  .pdf-badge-lo       { background: #E1F5EE; color: #085041; }

  .pdf-diff-neg { font-weight: 600; color: #A32D2D; }
  .pdf-diff-ok  { font-weight: 600; color: #0F6E56; }

  .pdf-recs {
    background: #f9fafb; border: 0.5px solid #e5e7eb;
    border-radius: 10px; padding: 16px 18px;
  }
  .pdf-recs-title {
    font-size: 12px; font-weight: 600; color: #111827;
    margin-bottom: 12px; display: flex; align-items: center; gap: 6px;
  }
  .pdf-recs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .pdf-recs-col-title { font-size: 11px; font-weight: 600; color: #374151; margin-bottom: 6px; }
  .pdf-recs ul { margin: 0; padding-left: 16px; }
  .pdf-recs ul li { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
  .pdf-recs-note {
    margin-top: 12px; padding: 10px 12px;
    background: #E6F1FB; border-radius: 7px;
    font-size: 11px; color: #185FA5;
  }

  .pdf-report-footer {
    text-align: center; font-size: 11px; color: #9ca3af;
    padding-top: 12px; border-top: 0.5px solid #f3f4f6;
  }

  .pdf-footer {
    padding: 14px 20px; border-top: 0.5px solid #f3f4f6;
    display: flex; align-items: center; gap: 8px;
    flex-shrink: 0;
  }
  .pdf-footer-spacer { flex: 1; }
  .pdf-btn {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 500;
    border-radius: 8px; padding: 7px 14px;
    cursor: pointer; transition: all 0.15s; border: none;
  }
  .pdf-btn-ghost {
    background: transparent; color: #6b7280;
    border: 0.5px solid #e5e7eb;
  }
  .pdf-btn-ghost:hover { background: #f9fafb; color: #111827; }
  .pdf-btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }
  .pdf-btn-danger {
    background: #FCEBEB; color: #A32D2D;
    border: 0.5px solid #F7C1C1;
  }
  .pdf-btn-danger:hover { background: #F7C1C1; }
  .pdf-btn-danger:disabled { opacity: 0.4; cursor: not-allowed; }
  .pdf-spinner {
    width: 13px; height: 13px; border: 2px solid rgba(163,45,45,0.3);
    border-top-color: #A32D2D; border-radius: 50%;
    animation: pdf-spin 0.6s linear infinite;
  }
  @keyframes pdf-spin { to { transform: rotate(360deg); } }

  @media (max-width: 600px) {
    .pdf-stats { grid-template-columns: repeat(2,1fr); }
    .pdf-recs-grid { grid-template-columns: 1fr; }
    .pdf-overlay { padding: 0; align-items: flex-end; }
    .pdf-modal { max-height: 95vh; border-radius: 12px 12px 0 0; }
  }
`;

// Iconos SVG inline
const IconFile = () => (
  <svg width="16" height="16" fill="none" stroke="#A32D2D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="9" y1="7" x2="15" y2="7"/>
  </svg>
);
const IconX = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" viewBox="0 0 24 24">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconAlert = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);
const IconCheck = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const IconDownload = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
);
const IconPrint = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="6 9 6 2 18 2 18 9"/>
    <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
    <rect x="6" y="14" width="12" height="8"/>
  </svg>
);
const IconExcel = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/>
  </svg>
);
const IconClipboard = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
    <rect x="8" y="2" width="8" height="4" rx="1"/>
  </svg>
);

const PDFLowStockReport = ({ lowStockProducts, onClose, activeFilter = 'all' }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const getFilterTitle = () => {
    if (activeFilter === 'outOfStock') return 'Productos agotados';
    if (activeFilter === 'critical')   return 'Productos con stock crítico';
    return 'Productos con bajo stock';
  };

  const getFilterDesc = () => {
    if (activeFilter === 'outOfStock') return 'Solo productos sin unidades disponibles';
    if (activeFilter === 'critical')   return 'Productos por debajo del mínimo establecido';
    return 'Todos los productos que requieren reabastecimiento';
  };

  const stats = {
    total:        lowStockProducts.length,
    outOfStock:   lowStockProducts.filter(p => p.stock === 0).length,
    critical:     lowStockProducts.filter(p => p.stock > 0 && p.stock <= (p.min_stock || 3)).length,
    totalDeficit: lowStockProducts.reduce((s, p) => s + Math.max(0, (p.min_stock || 3) - p.stock), 0),
  };

  const generatePDF = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.post('/reports/low-stock-pdf/', {
        products: lowStockProducts,
        date:     new Date().toISOString(),
        title:    getFilterTitle(),
        filter:   activeFilter,
      }, { responseType: 'blob' });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url  = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href     = url;
      link.download = `bajo-stock-${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => { document.body.removeChild(link); window.URL.revokeObjectURL(url); }, 100);

      setTimeout(onClose, 500);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.message || 'Error al generar el PDF. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = () => {
    const headers = ['#', 'Código', 'Producto', 'Stock actual', 'Stock mínimo', 'Diferencia', 'Estado'];
    const rows = lowStockProducts.map((p, i) => [
      i + 1,
      p.code || `P-${String(i + 1).padStart(3, '0')}`,
      p.name,
      p.stock,
      p.min_stock || 3,
      (p.min_stock || 3) - p.stock,
      p.stock === 0 ? 'Agotado' : p.stock <= (p.min_stock || 3) ? 'Crítico' : 'Bajo',
    ]);
    const csv  = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href     = url;
    link.download = `bajo-stock-${new Date().toISOString().slice(0, 10)}.csv`;
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const printReport = () => {
    const content = document.getElementById('pdf-report-preview');
    const win = window.open('', '', 'width=900,height=700');
    win.document.write(`
      <html>
        <head>
          <title>${getFilterTitle()}</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; color: #111827; font-size: 13px; }
            h2 { font-size: 18px; font-weight: 600; color: #111827; margin-bottom: 4px; }
            table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 16px; }
            th { padding: 7px 10px; text-align: left; background: #f9fafb; border-bottom: 1px solid #e5e7eb; font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em; color: #9ca3af; }
            td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; }
            .badge { display: inline-block; padding: 2px 7px; border-radius: 10px; font-size: 10px; font-weight: 500; }
            .badge-out      { background: #FCEBEB; color: #A32D2D; }
            .badge-critical { background: #FAEEDA; color: #854F0B; }
            .badge-low      { background: #E6F1FB; color: #185FA5; }
            .stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 16px 0; }
            .stat { background: #f9fafb; border-radius: 8px; padding: 10px 12px; text-align: center; }
            .stat-val { font-size: 20px; font-weight: 600; }
            .stat-lbl { font-size: 10px; color: #9ca3af; }
            .footer { margin-top: 24px; text-align: center; font-size: 10px; color: #9ca3af; border-top: 1px solid #f3f4f6; padding-top: 12px; }
          </style>
        </head>
        <body>${content.innerHTML}</body>
      </html>
    `);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 300);
  };

  const fmt = (n) => new Intl.NumberFormat('es-MX').format(n);

  const getBadge = (stock, minStock) => {
    if (stock === 0)          return { cls: 'pdf-badge-out',      text: 'Agotado'  };
    if (stock <= minStock)    return { cls: 'pdf-badge-critical', text: 'Crítico'  };
    return                         { cls: 'pdf-badge-low',       text: 'Bajo'     };
  };

  const getPriority = (stock, minStock) => {
    const diff = minStock - stock;
    if (stock === 0)  return { cls: 'pdf-badge-hi',  text: 'Alta'  };
    if (diff >= 5)    return { cls: 'pdf-badge-med', text: 'Media' };
    return                   { cls: 'pdf-badge-lo',  text: 'Baja'  };
  };

  return (
    <>
      <style>{styles}</style>
      <div className="pdf-overlay" onClick={onClose}>
        <div className="pdf-modal" onClick={e => e.stopPropagation()}>

          {/* Header */}
          <div className="pdf-header">
            <div className="pdf-header-icon"><IconFile /></div>
            <div className="pdf-header-info">
              <div className="pdf-header-title">{getFilterTitle()}</div>
              <div className="pdf-header-desc">{getFilterDesc()}</div>
            </div>
            <button className="pdf-close" onClick={onClose} disabled={loading}><IconX /></button>
          </div>

          {/* Body */}
          <div className="pdf-body">

            {/* Error */}
            {error && (
              <div className="pdf-error">
                <span><IconAlert /> {error}</span>
                <button className="pdf-error-close" onClick={() => setError(null)}><IconX /></button>
              </div>
            )}

            {/* Contenido del reporte (también sirve para imprimir) */}
            <div id="pdf-report-preview">

              {/* Stats */}
              <div className="pdf-stats">
                <div className="pdf-stat">
                  <div className="pdf-stat-val">{fmt(stats.total)}</div>
                  <div className="pdf-stat-lbl">Total productos</div>
                </div>
                <div className="pdf-stat">
                  <div className="pdf-stat-val" style={{ color: '#A32D2D' }}>{fmt(stats.outOfStock)}</div>
                  <div className="pdf-stat-lbl">Agotados</div>
                </div>
                <div className="pdf-stat">
                  <div className="pdf-stat-val" style={{ color: '#854F0B' }}>{fmt(stats.critical)}</div>
                  <div className="pdf-stat-lbl">Stock crítico</div>
                </div>
                <div className="pdf-stat">
                  <div className="pdf-stat-val">{fmt(stats.totalDeficit)}</div>
                  <div className="pdf-stat-lbl">Unidades faltantes</div>
                </div>
              </div>

              {/* Alertas */}
              {stats.outOfStock > 0 && (
                <div className="pdf-alert danger">
                  <IconAlert />
                  <div>
                    <div className="pdf-alert-title">Atención urgente requerida</div>
                    <div>Hay <strong>{stats.outOfStock}</strong> producto(s) completamente agotado(s) que requieren reabastecimiento inmediato.</div>
                  </div>
                </div>
              )}
              {stats.critical > 0 && (
                <div className="pdf-alert warn">
                  <IconAlert />
                  <div>
                    <div className="pdf-alert-title">Stock crítico detectado</div>
                    <div><strong>{stats.critical}</strong> producto(s) están por debajo del stock mínimo establecido.</div>
                  </div>
                </div>
              )}
              {stats.total === 0 && (
                <div className="pdf-alert success">
                  <IconCheck />
                  <div>
                    <div className="pdf-alert-title">Todo en orden</div>
                    <div>No hay productos que requieran atención en este momento.</div>
                  </div>
                </div>
              )}

              {/* Tabla */}
              {stats.total > 0 && (
                <div className="pdf-table-wrap">
                  <table className="pdf-table">
                    <thead>
                      <tr>
                        <th style={{ width: 36 }}>#</th>
                        <th style={{ width: 100 }}>Código</th>
                        <th>Producto</th>
                        <th className="c" style={{ width: 100 }}>Stock actual</th>
                        <th className="c" style={{ width: 90 }}>Mínimo</th>
                        <th className="c" style={{ width: 90 }}>Diferencia</th>
                        <th className="c" style={{ width: 100 }}>Estado</th>
                        <th className="c" style={{ width: 80 }}>Prioridad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lowStockProducts.map((product, index) => {
                        const minStock   = product.min_stock || 3;
                        const diff       = minStock - product.stock;
                        const badge      = getBadge(product.stock, minStock);
                        const priority   = getPriority(product.stock, minStock);
                        return (
                          <tr key={product.id || index}>
                            <td className="muted">{index + 1}</td>
                            <td className="muted" style={{ fontFamily: 'monospace', fontSize: 11 }}>
                              {product.code || `P-${String(index + 1).padStart(3, '0')}`}
                            </td>
                            <td>
                              <div style={{ fontWeight: 500 }}>{product.name}</div>
                              {product.description && (
                                <div className="muted">{product.description}</div>
                              )}
                            </td>
                            <td className="c">
                              <span className={`pdf-badge ${badge.cls}`}>{product.stock} un.</span>
                            </td>
                            <td className="c muted">{minStock} un.</td>
                            <td className="c">
                              <span className={diff > 0 ? 'pdf-diff-neg' : 'pdf-diff-ok'}>
                                {diff > 0 ? `−${diff}` : '0'}
                              </span>
                            </td>
                            <td className="c">
                              <span className={`pdf-badge ${badge.cls}`}>{badge.text}</span>
                            </td>
                            <td className="c">
                              <span className={`pdf-badge ${priority.cls}`}>{priority.text}</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Recomendaciones */}
              <div className="pdf-recs">
                <div className="pdf-recs-title">
                  <IconClipboard /> Recomendaciones y acciones sugeridas
                </div>
                <div className="pdf-recs-grid">
                  <div>
                    <div className="pdf-recs-col-title">Acciones inmediatas</div>
                    <ul>
                      <li>Contactar a proveedores de productos agotados</li>
                      <li>Verificar pedidos pendientes en tránsito</li>
                      <li>Evaluar opciones de productos sustitutos</li>
                      <li>Comunicar al equipo de ventas sobre disponibilidad</li>
                    </ul>
                  </div>
                  <div>
                    <div className="pdf-recs-col-title">Prevención</div>
                    <ul>
                      <li>Establecer alertas automáticas de stock bajo</li>
                      <li>Revisar y ajustar stock mínimo según demanda</li>
                      <li>Implementar sistema de reorden automático</li>
                      <li>Analizar patrones de consumo históricos</li>
                    </ul>
                  </div>
                </div>
                <div className="pdf-recs-note">
                  Se recomienda realizar una revisión periódica del inventario y ajustar los niveles mínimos según la rotación y tendencias de venta.
                </div>
              </div>

              {/* Footer del reporte */}
              <div className="pdf-report-footer">
                <div>Sistema de gestión de inventario · Reporte generado el {new Date().toLocaleDateString('es-MX', { day: '2-digit', month: 'long', year: 'numeric' })}</div>
              </div>

            </div>
          </div>

          {/* Footer de acciones */}
          <div className="pdf-footer">
            <button className="pdf-btn pdf-btn-ghost" onClick={onClose} disabled={loading}>
              <IconX /> Cerrar
            </button>
            <div className="pdf-footer-spacer" />
            <button
              className="pdf-btn pdf-btn-ghost"
              onClick={exportToCSV}
              disabled={loading || stats.total === 0}
            >
              <IconExcel /> Exportar CSV
            </button>
            <button
              className="pdf-btn pdf-btn-ghost"
              onClick={printReport}
              disabled={loading || stats.total === 0}
            >
              <IconPrint /> Imprimir
            </button>
            <button
              className="pdf-btn pdf-btn-danger"
              onClick={generatePDF}
              disabled={loading || stats.total === 0}
            >
              {loading ? (
                <><div className="pdf-spinner" /> Generando...</>
              ) : (
                <><IconDownload /> Descargar PDF</>
              )}
            </button>
          </div>

        </div>
      </div>
    </>
  );
};

export default PDFLowStockReport;