import React, { useState } from 'react';
import api from '../services/api';
import {
  IconFile,
  IconX,
  IconAlert,
  IconCheck,
  IconDownload,
  IconPrint,
  IconExcel,
  IconClipboard,
} from './Icons';
import '../css/LowStockReports.css';


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
      <div className="pdf-overlay" onClick={onClose}>
        <div className="pdf-modal" onClick={e => e.stopPropagation()}>

          {/* Header */}
          <div className="pdf-header">
            <div className="pdf-header-icon"><IconFile stroke="#6C63FF" /></div>
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
                  <div className="pdf-stat-val danger">{fmt(stats.outOfStock)}</div>
                  <div className="pdf-stat-lbl">Agotados</div>
                </div>
                <div className="pdf-stat">
                  <div className="pdf-stat-val warn">{fmt(stats.critical)}</div>
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
                              <div className="pdf-product-name">{product.name}</div>
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
