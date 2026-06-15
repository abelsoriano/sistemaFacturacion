import React, { useState, useEffect } from 'react';
import PDFLowStockReport from './PDFLowStockReport';
import api from '../services/api';
import { showSuccessAlert, showErrorAlert } from '../herpert';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import {
  IconArrowLeft,
  IconRefresh,
  IconExcel,
  IconPDF,
  IconAlert,
  IconBox,
  IconFilter,
} from './Icons';
import '../css/LowStockReports.css';


const LowStockProducts = ({ onBack }) => {
  const [products, setProducts]         = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [showPDFModal, setShowPDFModal] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all');
  const [restockProduct, setRestockProduct] = useState(null);
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
      <div className="ls-shell">

        <nav className="ls-nav">
          <div className="ls-nav-heading">
            <span className="ls-nav-icon"><IconAlert /></span>
            <div>
              <div className="ls-nav-title">Reporte de bajo stock</div>
              <div className="ls-nav-subtitle">Monitorea productos que requieren reabastecimiento y exporta reportes operativos.</div>
            </div>
          </div>

          <div className="ls-nav-actions">
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
          </div>
        </nav>

        <div className="ls-body">

          {/* Error */}
          {error && (
            <div className="ls-error">
              <IconAlert />
              <div>
                <div className="ls-error-title">Error al cargar los datos</div>
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
                        <td className="muted" data-label="#">{index + 1}</td>
                        <td data-label="Producto">
                          <div className="ls-product-name">{product.name}</div>
                          {product.barcode && (
                            <div className="muted">{product.barcode}</div>
                          )}
                          {product.category_name && (
                            <div className="muted">{product.category_name}</div>
                          )}
                        </td>
                        <td className="c" data-label="Stock actual">
                          <div className="ls-stock-bar-wrap">
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
                        <td className="c muted" data-label="Mínimo">{product.min_stock || 3}</td>
                        <td className="c" data-label="Estado">
                          <span className={`ls-badge ${status.badgeClass}`}>{status.text}</span>
                        </td>
                        <td data-label="Acción">
                          <button
                            className="ls-restock-btn"
                            onClick={() => setRestockProduct(product)}
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

        {restockProduct && (
          <div
            className="ls-modal-overlay"
            onClick={(event) => {
              if (event.target === event.currentTarget) setRestockProduct(null);
            }}
          >
            <div className="ls-info-modal" role="dialog" aria-modal="true" aria-labelledby="restock-modal-title">
              <div className="ls-info-modal-icon">
                <IconBox />
              </div>
              <div className="ls-info-modal-content">
                <div id="restock-modal-title" className="ls-info-modal-title">
                  Reabastecimiento pendiente
                </div>
                <p>
                  El producto <strong>{restockProduct.name}</strong> requiere reposición. El flujo de
                  compra/reabastecimiento estará disponible en una próxima fase.
                </p>
                <div className="ls-info-modal-meta">
                  Stock actual: <strong>{restockProduct.stock}</strong> · Mínimo sugerido:{' '}
                  <strong>{restockProduct.min_stock || 3}</strong>
                </div>
              </div>
              <div className="ls-info-modal-actions">
                <button className="ls-btn ls-btn-danger" onClick={() => setRestockProduct(null)}>
                  Entendido
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default LowStockProducts;
