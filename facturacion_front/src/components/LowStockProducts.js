import React, { useState, useEffect } from 'react';
import PDFLowStockReport from './PDFLowStockReport';
import api from '../services/api';
import { showSuccessAlert, showErrorAlert } from '../herpert';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';

const styles = `
  .ls-shell { background: #f4f5f7; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

  .ls-nav {
    background: #fff; border-bottom: 0.5px solid #e5e7eb;
    padding: 0 24px; height: 56px;
    display: flex; align-items: center; gap: 12px;
    position: sticky; top: 0; z-index: 100;
  }
  .ls-nav-back {
    display: flex; align-items: center; gap: 5px;
    font-size: 12px; color: #6b7280;
    background: transparent; border: 0.5px solid #e5e7eb;
    border-radius: 8px; padding: 5px 12px; cursor: pointer;
    transition: background 0.15s;
  }
  .ls-nav-back:hover { background: #f9fafb; }
  .ls-nav-title { font-size: 15px; font-weight: 600; color: #111827; flex: 1; }
  .ls-btn {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 500;
    border-radius: 8px; padding: 6px 14px;
    cursor: pointer; transition: all 0.15s; border: none;
  }
  .ls-btn-ghost {
    background: transparent; color: #6b7280;
    border: 0.5px solid #e5e7eb;
  }
  .ls-btn-ghost:hover { background: #f9fafb; color: #111827; }
  .ls-btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }
  .ls-btn-danger {
    background: #FCEBEB; color: #A32D2D;
    border: 0.5px solid #F7C1C1;
  }
  .ls-btn-danger:hover { background: #F7C1C1; }
  .ls-btn-danger:disabled { opacity: 0.4; cursor: not-allowed; }

  .ls-body { max-width: 1100px; margin: 0 auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }

  .ls-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .ls-stat {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; padding: 14px 16px;
    cursor: pointer; transition: border-color 0.15s;
  }
  .ls-stat:hover { border-color: #9ca3af; }
  .ls-stat.active-all    { border-color: #1D9E75; background: #f0fdf8; }
  .ls-stat.active-critical { border-color: #BA7517; background: #fffbeb; }
  .ls-stat.active-out    { border-color: #A32D2D; background: #fff5f5; }
  .ls-stat-lbl {
    font-size: 10px; font-weight: 600; color: #9ca3af;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;
    display: flex; align-items: center; gap: 5px;
  }
  .ls-stat-lbl.teal   { color: #0F6E56; }
  .ls-stat-lbl.amber  { color: #854F0B; }
  .ls-stat-lbl.red    { color: #A32D2D; }
  .ls-stat-val { font-size: 22px; font-weight: 600; color: #111827; }
  .ls-stat-sub { font-size: 11px; color: #9ca3af; margin-top: 3px; }
  .ls-active-pill {
    display: inline-block; font-size: 10px; font-weight: 500;
    padding: 2px 8px; border-radius: 10px; margin-top: 6px;
  }
  .ls-active-pill.teal  { background: #E1F5EE; color: #085041; }
  .ls-active-pill.amber { background: #FAEEDA; color: #633806; }
  .ls-active-pill.red   { background: #FCEBEB; color: #791F1F; }

  .ls-filters {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; padding: 10px 16px;
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
  }
  .ls-filter-btns { display: flex; gap: 6px; }
  .ls-filter-btn {
    font-size: 12px; font-weight: 500;
    padding: 5px 12px; border-radius: 20px;
    cursor: pointer; transition: all 0.12s;
    background: #f9fafb; border: 0.5px solid #e5e7eb; color: #6b7280;
  }
  .ls-filter-btn:hover { border-color: #9ca3af; color: #111827; }
  .ls-filter-btn.active-all      { background: #E1F5EE; color: #085041; border-color: #5DCAA5; }
  .ls-filter-btn.active-critical { background: #FAEEDA; color: #633806; border-color: #EF9F27; }
  .ls-filter-btn.active-out      { background: #FCEBEB; color: #791F1F; border-color: #F09595; }
  .ls-count-pill {
    font-size: 11px; color: #6b7280;
    background: #f3f4f6; border-radius: 10px;
    padding: 3px 10px;
  }

  .ls-table-card {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; overflow: hidden;
  }
  .ls-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .ls-table thead th {
    padding: 9px 16px; text-align: left;
    font-size: 10px; font-weight: 600; color: #9ca3af;
    background: #f9fafb; border-bottom: 0.5px solid #f3f4f6;
    text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
  }
  .ls-table thead th.c { text-align: center; }
  .ls-table tbody tr { border-bottom: 0.5px solid #f9fafb; transition: background 0.1s; }
  .ls-table tbody tr:last-child { border-bottom: none; }
  .ls-table tbody tr:hover { background: #f9fafb; }
  .ls-table tbody td { padding: 11px 16px; vertical-align: middle; color: #111827; }
  .ls-table tbody td.muted { color: #9ca3af; font-size: 12px; }
  .ls-table tbody td.c { text-align: center; }

  .ls-stock-bar-wrap {
    display: flex; align-items: center; gap: 8px;
  }
  .ls-stock-bar-bg {
    flex: 1; height: 4px; background: #f3f4f6;
    border-radius: 2px; overflow: hidden; max-width: 80px;
  }
  .ls-stock-bar-fill { height: 100%; border-radius: 2px; }
  .ls-stock-num { font-size: 13px; font-weight: 600; }

  .ls-badge {
    display: inline-block; font-size: 10px; font-weight: 500;
    padding: 3px 9px; border-radius: 10px;
  }
  .ls-badge-out      { background: #FCEBEB; color: #A32D2D; }
  .ls-badge-critical { background: #FAEEDA; color: #854F0B; }
  .ls-badge-low      { background: #E6F1FB; color: #185FA5; }

  .ls-restock-btn {
    font-size: 12px; font-weight: 500;
    padding: 5px 12px; border-radius: 7px;
    background: transparent; border: 0.5px solid #e5e7eb;
    color: #374151; cursor: pointer; transition: all 0.12s;
  }
  .ls-restock-btn:hover { background: #E1F5EE; color: #0F6E56; border-color: #5DCAA5; }

  .ls-empty { padding: 56px; text-align: center; color: #9ca3af; }
  .ls-empty-icon { font-size: 44px; opacity: 0.2; margin-bottom: 12px; }
  .ls-empty p { font-size: 14px; margin-bottom: 12px; }
  .ls-show-all-btn {
    font-size: 12px; padding: 6px 14px; border-radius: 8px;
    background: transparent; border: 0.5px solid #e5e7eb;
    color: #374151; cursor: pointer;
  }
  .ls-show-all-btn:hover { background: #f9fafb; }

  .ls-loading { padding: 56px; text-align: center; color: #9ca3af; font-size: 13px; }
  .ls-spinner {
    width: 24px; height: 24px; border: 2px solid #e5e7eb;
    border-top-color: #1D9E75; border-radius: 50%;
    animation: ls-spin 0.6s linear infinite; margin: 0 auto 12px;
  }
  @keyframes ls-spin { to { transform: rotate(360deg); } }

  .ls-error {
    background: #FCEBEB; border: 0.5px solid #F7C1C1;
    border-radius: 10px; padding: 16px 20px;
    display: flex; align-items: flex-start; gap: 12px;
    font-size: 13px; color: #A32D2D;
  }
  .ls-error-actions { display: flex; gap: 8px; margin-top: 10px; }

  @media (max-width: 768px) {
    .ls-stats { grid-template-columns: 1fr; }
    .ls-nav-title { display: none; }
  }
`;

// Iconos SVG inline
const IconArrowLeft = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
  </svg>
);
const IconRefresh = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="23 4 23 10 17 10"/>
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
);
const IconExcel = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/>
  </svg>
);
const IconPDF = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="9" y1="7" x2="15" y2="7"/>
  </svg>
);
const IconAlert = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);
const IconBox = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
  </svg>
);
const IconFilter = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
  </svg>
);

const LowStockProducts = ({ onBack }) => {
  const [products, setProducts]         = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [showPDFModal, setShowPDFModal] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all');
  const navigate = useNavigate();

  const handleBack = () => {
    if (onBack) onBack();
    else navigate('/home');
  };

  const fetchLowStockProducts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/products/?low_stock=true');
      setProducts(response.data);
    } catch (err) {
      console.error(err);
      setError('Error al cargar los productos con bajo stock');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLowStockProducts(); }, []);

  const getStockStatus = (stock, minStock = 3) => {
    if (stock === 0)          return { text: 'Agotado',       key: 'out',      barColor: '#E24B4A', badgeClass: 'ls-badge-out'      };
    if (stock <= minStock)    return { text: 'Stock crítico',  key: 'critical', barColor: '#EF9F27', badgeClass: 'ls-badge-critical'  };
    return                         { text: 'Bajo stock',      key: 'low',      barColor: '#378ADD', badgeClass: 'ls-badge-low'       };
  };

  const filteredProducts = products.filter(p => {
    if (activeFilter === 'outOfStock') return p.stock === 0;
    if (activeFilter === 'critical')   return p.stock > 0 && p.stock <= (p.min_stock || 3);
    return true;
  });

  const criticalCount  = products.filter(p => p.stock > 0 && p.stock <= (p.min_stock || 3)).length;
  const outOfStockCount = products.filter(p => p.stock === 0).length;

  const exportToExcel = () => {
    try {
      const ws = XLSX.utils.json_to_sheet(filteredProducts.map(p => ({
        Nombre:          p.name,
        Categoría:       p.category_name || 'Sin categoría',
        Stock:           p.stock,
        'Stock mínimo':  p.min_stock || 3,
        Precio:          p.price,
        Código:          p.barcode || '-',
      })));
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'BajoStock');
      XLSX.writeFile(wb, 'productos_bajo_stock.xlsx');
      showSuccessAlert('Exportación completada', 'El reporte se descargó correctamente.');
    } catch (err) {
      showErrorAlert('Error', 'No se pudo generar el archivo Excel.');
    }
  };

  const getBarPercent = (stock, minStock = 3) => {
    if (stock === 0) return 0;
    return Math.min(100, Math.round((stock / (minStock * 2)) * 100));
  };

  return (
    <>
      <style>{styles}</style>
      <div className="ls-shell">

        {/* Navbar */}
        <nav className="ls-nav">
          <button className="ls-nav-back" onClick={handleBack}>
            <IconArrowLeft /> Volver
          </button>
          <span className="ls-nav-title">Bajo stock</span>

          <button className="ls-btn ls-btn-ghost" onClick={fetchLowStockProducts} title="Actualizar">
            <IconRefresh /> Actualizar
          </button>
          <button
            className="ls-btn ls-btn-ghost"
            onClick={exportToExcel}
            disabled={filteredProducts.length === 0}
          >
            <IconExcel /> Exportar Excel
          </button>
          <button
            className="ls-btn ls-btn-danger"
            onClick={() => setShowPDFModal(true)}
            disabled={products.length === 0}
          >
            <IconPDF /> Generar PDF
          </button>
        </nav>

        <div className="ls-body">

          {/* Error */}
          {error && (
            <div className="ls-error">
              <IconAlert />
              <div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Error al cargar los datos</div>
                <div>{error}</div>
                <div className="ls-error-actions">
                  <button className="ls-btn ls-btn-ghost" onClick={fetchLowStockProducts}>
                    <IconRefresh /> Reintentar
                  </button>
                  <button className="ls-btn ls-btn-ghost" onClick={handleBack}>
                    <IconArrowLeft /> Volver
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Stats / filtros de tarjeta */}
          <div className="ls-stats">
            <div
              className={`ls-stat${activeFilter === 'all' ? ' active-all' : ''}`}
              onClick={() => setActiveFilter('all')}
            >
              <div className={`ls-stat-lbl${activeFilter === 'all' ? ' teal' : ''}`}>
                <IconBox /> Total con bajo stock
              </div>
              <div className="ls-stat-val">{loading ? '—' : products.length}</div>
              <div className="ls-stat-sub">productos registrados</div>
              {activeFilter === 'all' && (
                <span className="ls-active-pill teal"><IconFilter /> Filtro activo</span>
              )}
            </div>

            <div
              className={`ls-stat${activeFilter === 'critical' ? ' active-critical' : ''}`}
              onClick={() => setActiveFilter('critical')}
            >
              <div className={`ls-stat-lbl${activeFilter === 'critical' ? ' amber' : ''}`}>
                <IconAlert /> Stock crítico
              </div>
              <div className="ls-stat-val">{loading ? '—' : criticalCount}</div>
              <div className="ls-stat-sub">por debajo del mínimo</div>
              {activeFilter === 'critical' && (
                <span className="ls-active-pill amber"><IconFilter /> Filtro activo</span>
              )}
            </div>

            <div
              className={`ls-stat${activeFilter === 'outOfStock' ? ' active-out' : ''}`}
              onClick={() => setActiveFilter('outOfStock')}
            >
              <div className={`ls-stat-lbl${activeFilter === 'outOfStock' ? ' red' : ''}`}>
                <IconBox /> Agotados
              </div>
              <div className="ls-stat-val">{loading ? '—' : outOfStockCount}</div>
              <div className="ls-stat-sub">sin unidades disponibles</div>
              {activeFilter === 'outOfStock' && (
                <span className="ls-active-pill red"><IconFilter /> Filtro activo</span>
              )}
            </div>
          </div>

          {/* Filtros rápidos */}
          <div className="ls-filters">
            <div className="ls-filter-btns">
              <button
                className={`ls-filter-btn${activeFilter === 'all' ? ' active-all' : ''}`}
                onClick={() => setActiveFilter('all')}
              >
                Todos ({products.length})
              </button>
              <button
                className={`ls-filter-btn${activeFilter === 'critical' ? ' active-critical' : ''}`}
                onClick={() => setActiveFilter('critical')}
              >
                Stock crítico ({criticalCount})
              </button>
              <button
                className={`ls-filter-btn${activeFilter === 'outOfStock' ? ' active-out' : ''}`}
                onClick={() => setActiveFilter('outOfStock')}
              >
                Agotados ({outOfStockCount})
              </button>
            </div>
            <span className="ls-count-pill">
              {filteredProducts.length} de {products.length} productos
            </span>
          </div>

          {/* Tabla */}
          <div className="ls-table-card">
            {loading ? (
              <div className="ls-loading">
                <div className="ls-spinner" />
                Cargando productos...
              </div>
            ) : filteredProducts.length === 0 ? (
              <div className="ls-empty">
                <div className="ls-empty-icon">📦</div>
                <p>
                  {activeFilter === 'all'
                    ? 'No hay productos con bajo stock en este momento.'
                    : `No hay productos en "${activeFilter === 'critical' ? 'Stock crítico' : 'Agotados'}".`}
                </p>
                {activeFilter !== 'all' && (
                  <button className="ls-show-all-btn" onClick={() => setActiveFilter('all')}>
                    Ver todos los productos
                  </button>
                )}
              </div>
            ) : (
              <table className="ls-table">
                <thead>
                  <tr>
                    <th style={{ width: 48 }}>#</th>
                    <th>Producto</th>
                    <th className="c" style={{ width: 160 }}>Stock actual</th>
                    <th className="c" style={{ width: 130 }}>Mínimo</th>
                    <th className="c" style={{ width: 130 }}>Estado</th>
                    <th style={{ width: 120 }}>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducts.map((product, index) => {
                    const status  = getStockStatus(product.stock, product.min_stock);
                    const pct     = getBarPercent(product.stock, product.min_stock || 3);
                    return (
                      <tr key={product.id}>
                        <td className="muted">{index + 1}</td>
                        <td>
                          <div style={{ fontWeight: 500, color: '#111827' }}>{product.name}</div>
                          {product.barcode && (
                            <div className="muted">{product.barcode}</div>
                          )}
                          {product.category_name && (
                            <div className="muted">{product.category_name}</div>
                          )}
                        </td>
                        <td className="c">
                          <div className="ls-stock-bar-wrap" style={{ justifyContent: 'center' }}>
                            <div className="ls-stock-bar-bg">
                              <div
                                className="ls-stock-bar-fill"
                                style={{ width: `${pct}%`, background: status.barColor }}
                              />
                            </div>
                            <span
                              className="ls-stock-num"
                              style={{ color: status.barColor, minWidth: 28 }}
                            >
                              {product.stock}
                            </span>
                          </div>
                        </td>
                        <td className="c muted">{product.min_stock || 3}</td>
                        <td className="c">
                          <span className={`ls-badge ${status.badgeClass}`}>{status.text}</span>
                        </td>
                        <td>
                          <button
                            className="ls-restock-btn"
                            onClick={() => alert(`Reabastecer: ${product.name}`)}
                          >
                            Reabastecer
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Modal PDF */}
        {showPDFModal && (
          <PDFLowStockReport
            lowStockProducts={filteredProducts}
            activeFilter={activeFilter}
            onClose={() => setShowPDFModal(false)}
          />
        )}
      </div>
    </>
  );
};

export default LowStockProducts;