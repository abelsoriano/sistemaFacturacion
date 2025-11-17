import React, { useState } from 'react';
import { FaFilePdf, FaPrint, FaDownload, FaExclamationTriangle, FaCheckCircle, FaTimes, FaFileExcel } from 'react-icons/fa';
import api from '../services/api';

const PDFLowStockReport = ({ lowStockProducts, onClose, activeFilter = 'all' }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getFilterTitle = () => {
    switch(activeFilter) {
      case 'outOfStock': return 'Productos Agotados';
      case 'critical': return 'Productos con Stock Crítico';
      default: return 'Productos con Bajo Stock';
    }
  };

  const getFilterDescription = () => {
    switch(activeFilter) {
      case 'outOfStock': return 'Este reporte incluye únicamente productos sin stock disponible';
      case 'critical': return 'Este reporte incluye productos con stock por debajo del mínimo establecido';
      default: return 'Este reporte incluye todos los productos que requieren reabastecimiento';
    }
  };

  const generatePDF = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Simulación de API call - Reemplaza con tu llamada real
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Descomenta y usa tu API real:
  
      const response = await api.post('/reports/low-stock-pdf/', {
        products: lowStockProducts,
        date: new Date().toISOString(),
        title: getFilterTitle(),
        filter: activeFilter
      }, {
        responseType: 'blob'
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `productos-bajo-stock-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
     
      
      // alert(`PDF generado exitosamente con ${lowStockProducts.length} productos`);
      
      setTimeout(() => {
        onClose();
      }, 500);
      
    } catch (error) {
      console.error('Error generando PDF:', error);
      setError(error.response?.data?.message || 'Error al generar el PDF. Por favor, intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const exportToExcel = () => {
    // Crear CSV
    const headers = ['#', 'Código', 'Producto', 'Descripción', 'Stock Actual', 'Stock Mínimo', 'Diferencia', 'Estado'];
    const rows = lowStockProducts.map((product, index) => [
      index + 1,
      product.code || `P-${String(index + 1).padStart(3, '0')}`,
      product.name,
      product.description || '',
      product.stock,
      product.min_stock || 3,
      (product.min_stock || 3) - product.stock,
      product.stock === 0 ? 'Agotado' : product.stock <= (product.min_stock || 3) ? 'Crítico' : 'Bajo'
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `productos-bajo-stock-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const printReport = () => {
    const printContent = document.getElementById('report-preview');
    const windowPrint = window.open('', '', 'width=900,height=700');
    
    windowPrint.document.write(`
      <html>
        <head>
          <title>${getFilterTitle()}</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
          <style>
            body { 
              padding: 20px; 
              font-family: 'Arial', sans-serif;
              color: #333;
            }
            @media print {
              .no-print { display: none; }
              @page { margin: 1.5cm; }
              body { padding: 0; }
            }
            .header-section { 
              border-bottom: 4px solid #dc3545; 
              padding-bottom: 20px; 
              margin-bottom: 25px; 
            }
            .stats-card {
              border: 2px solid #dee2e6;
              border-radius: 8px;
              padding: 15px;
              margin-bottom: 15px;
            }
            table { 
              font-size: 11px;
              width: 100%;
            }
            .badge { 
              padding: 4px 8px; 
              border-radius: 4px;
              font-size: 10px;
              font-weight: 600;
            }
            .bg-danger { 
              background-color: #dc3545 !important; 
              color: white !important; 
            }
            .bg-warning { 
              background-color: #ffc107 !important; 
              color: black !important; 
            }
            .bg-info { 
              background-color: #0dcaf0 !important; 
              color: black !important; 
            }
            .text-danger { color: #dc3545 !important; }
            .text-warning { color: #ffc107 !important; }
            .text-success { color: #198754 !important; }
            .fw-bold { font-weight: 700 !important; }
            .recommendations {
              background-color: #fff3cd;
              border-left: 4px solid #ffc107;
              padding: 15px;
              margin-top: 20px;
            }
            .footer-section {
              margin-top: 30px;
              padding-top: 20px;
              border-top: 2px solid #dee2e6;
              text-align: center;
              font-size: 10px;
              color: #6c757d;
            }
          </style>
        </head>
        <body>
          ${printContent.innerHTML}
        </body>
      </html>
    `);
    
    windowPrint.document.close();
    windowPrint.focus();
    
    setTimeout(() => {
      windowPrint.print();
    }, 300);
  };

  // Calcular estadísticas
  const stats = {
    total: lowStockProducts.length,
    outOfStock: lowStockProducts.filter(p => p.stock === 0).length,
    critical: lowStockProducts.filter(p => p.stock > 0 && p.stock <= (p.min_stock || 3)).length,
    totalDeficit: lowStockProducts.reduce((sum, p) => sum + Math.max(0, (p.min_stock || 3) - p.stock), 0)
  };

  return (
    <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
      <div className="modal-dialog modal-xl modal-dialog-scrollable">
        <div className="modal-content">
          {/* Header */}
          <div className="modal-header bg-danger text-white">
            <div>
              <h5 className="modal-title mb-1">
                <FaFilePdf className="me-2" />
                {getFilterTitle()}
              </h5>
              <small className="opacity-75">{getFilterDescription()}</small>
            </div>
            <button 
              type="button" 
              className="btn-close btn-close-white" 
              onClick={onClose}
              disabled={loading}
            ></button>
          </div>
          
          {/* Body */}
          <div className="modal-body p-4" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            {error && (
              <div className="alert alert-danger alert-dismissible fade show" role="alert">
                <FaTimes className="me-2" />
                <strong>Error:</strong> {error}
                <button 
                  type="button" 
                  className="btn-close" 
                  onClick={() => setError(null)}
                ></button>
              </div>
            )}

            {/* Vista previa del reporte */}
            <div className="report-preview bg-white" id="report-preview">
              {/* Header del reporte */}
              <div className="header-section text-center">
                <h2 className="text-danger mb-2 fw-bold">{getFilterTitle()}</h2>
                <p className="text-muted mb-2">
                  <strong>Fecha de generación:</strong> {new Date().toLocaleDateString('es-ES', { 
                    weekday: 'long',
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric'
                  })} - {new Date().toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
                {activeFilter !== 'all' && (
                  <span className="badge bg-secondary fs-6">
                    Filtro aplicado: {activeFilter === 'outOfStock' ? 'Solo Agotados' : 'Solo Stock Crítico'}
                  </span>
                )}
              </div>

              {/* Resumen ejecutivo */}
              <div className="row mb-4">
                <div className="col-md-3">
                  <div className="card border-primary h-100">
                    <div className="card-body text-center py-3">
                      <div className="text-primary fs-1 fw-bold mb-1">{stats.total}</div>
                      <div className="text-muted small">Total Productos</div>
                    </div>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="card border-danger h-100">
                    <div className="card-body text-center py-3">
                      <div className="text-danger fs-1 fw-bold mb-1">{stats.outOfStock}</div>
                      <div className="text-muted small">Agotados</div>
                    </div>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="card border-warning h-100">
                    <div className="card-body text-center py-3">
                      <div className="text-warning fs-1 fw-bold mb-1">{stats.critical}</div>
                      <div className="text-muted small">Stock Crítico</div>
                    </div>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="card border-info h-100">
                    <div className="card-body text-center py-3">
                      <div className="text-info fs-1 fw-bold mb-1">{stats.totalDeficit}</div>
                      <div className="text-muted small">Unidades Faltantes</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Análisis rápido */}
              {stats.outOfStock > 0 && (
                <div className="alert alert-danger d-flex align-items-start mb-4">
                  <FaExclamationTriangle className="me-3 mt-1 fs-4" />
                  <div>
                    <h6 className="alert-heading mb-1">Atención Urgente Requerida</h6>
                    <p className="mb-0 small">
                      Hay <strong>{stats.outOfStock}</strong> producto(s) completamente agotado(s) que requieren reabastecimiento inmediato.
                    </p>
                  </div>
                </div>
              )}

              {stats.critical > 0 && (
                <div className="alert alert-warning d-flex align-items-start mb-4">
                  <FaExclamationTriangle className="me-3 mt-1 fs-4" />
                  <div>
                    <h6 className="alert-heading mb-1">Stock Crítico Detectado</h6>
                    <p className="mb-0 small">
                      <strong>{stats.critical}</strong> producto(s) están por debajo del stock mínimo establecido.
                    </p>
                  </div>
                </div>
              )}

              {stats.total === 0 && (
                <div className="alert alert-success d-flex align-items-center mb-4">
                  <FaCheckCircle className="me-3 fs-4" />
                  <div>
                    <h6 className="alert-heading mb-1">¡Todo en orden!</h6>
                    <p className="mb-0 small">No hay productos que requieran atención en este momento.</p>
                  </div>
                </div>
              )}

              {/* Tabla de productos */}
              {stats.total > 0 && (
                <div className="table-responsive mb-4">
                  <table className="table table-hover table-bordered align-middle">
                    <thead className="table-danger">
                      <tr>
                        <th style={{ width: '5%' }} className="text-center">#</th>
                        <th style={{ width: '12%' }}>Código</th>
                        <th style={{ width: '28%' }}>Producto</th>
                        <th style={{ width: '10%' }} className="text-center">Stock Actual</th>
                        <th style={{ width: '10%' }} className="text-center">Stock Mínimo</th>
                        <th style={{ width: '10%' }} className="text-center">Diferencia</th>
                        <th style={{ width: '12%' }} className="text-center">Estado</th>
                        <th style={{ width: '13%' }} className="text-center">Prioridad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lowStockProducts.map((product, index) => {
                        const difference = (product.min_stock || 3) - product.stock;
                        const priority = product.stock === 0 ? 'Alta' : difference >= 5 ? 'Media' : 'Baja';
                        const priorityColor = priority === 'Alta' ? 'danger' : priority === 'Media' ? 'warning' : 'info';
                        
                        return (
                          <tr key={product.id || index} className={product.stock === 0 ? 'table-danger' : ''}>
                            <td className="text-center fw-bold">{index + 1}</td>
                            <td>
                              <code className="text-dark">
                                {product.code || `P-${String(index + 1).padStart(3, '0')}`}
                              </code>
                            </td>
                            <td>
                              <div className="fw-bold text-dark">{product.name}</div>
                              {product.description && (
                                <small className="text-muted d-block mt-1">{product.description}</small>
                              )}
                            </td>
                            <td className="text-center">
                              <span className={`badge ${product.stock === 0 ? 'bg-danger' : product.stock <= (product.min_stock || 3) ? 'bg-warning text-dark' : 'bg-info text-dark'}`}>
                                {product.stock} un.
                              </span>
                            </td>
                            <td className="text-center text-muted">
                              {product.min_stock || 3} un.
                            </td>
                            <td className="text-center">
                              <span className={`fw-bold ${difference > 0 ? 'text-danger' : 'text-success'}`}>
                                {difference > 0 ? `-${difference}` : '0'}
                              </span>
                            </td>
                            <td className="text-center">
                              {product.stock === 0 ? (
                                <span className="badge bg-danger">Agotado</span>
                              ) : product.stock <= (product.min_stock || 3) ? (
                                <span className="badge bg-warning text-dark">Crítico</span>
                              ) : (
                                <span className="badge bg-info text-dark">Bajo</span>
                              )}
                            </td>
                            <td className="text-center">
                              <span className={`badge bg-${priorityColor}`}>
                                {priority}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Recomendaciones */}
              <div className="card border-warning mb-4">
                <div className="card-header bg-warning bg-opacity-25">
                  <h6 className="mb-0 fw-bold">
                    <FaExclamationTriangle className="me-2 text-warning" />
                    Recomendaciones y Acciones Sugeridas
                  </h6>
                </div>
                <div className="card-body">
                  <div className="row">
                    <div className="col-md-6">
                      <h6 className="text-danger fw-bold mb-2">Acciones Inmediatas:</h6>
                      <ul className="small mb-3">
                        <li>Contactar a proveedores de productos agotados</li>
                        <li>Verificar pedidos pendientes en tránsito</li>
                        <li>Evaluar opciones de productos sustitutos</li>
                        <li>Comunicar a equipo de ventas sobre disponibilidad</li>
                      </ul>
                    </div>
                    <div className="col-md-6">
                      <h6 className="text-warning fw-bold mb-2">Prevención:</h6>
                      <ul className="small mb-3">
                        <li>Establecer alertas automáticas de stock bajo</li>
                        <li>Revisar y ajustar stock mínimo según demanda</li>
                        <li>Implementar sistema de reorden automático</li>
                        <li>Analizar patrones de consumo históricos</li>
                      </ul>
                    </div>
                  </div>
                  <div className="alert alert-info mb-0 small">
                    <strong>Nota:</strong> Se recomienda realizar una revisión completa del inventario y ajustar los niveles de stock mínimo basándose en la rotación de productos y tendencias de venta.
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="footer-section mt-4 pt-3 border-top text-center">
                <p className="text-muted small mb-2">
                  <strong>Sistema de Gestión de Inventario</strong> | Reporte generado automáticamente
                </p>
                <p className="text-muted small mb-0">
                  Para más información o asistencia, contacte al Departamento de Logística
                </p>
              </div>
            </div>
          </div>

          {/* Footer con acciones */}
          <div className="modal-footer bg-light">
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={onClose}
              disabled={loading}
            >
              <FaTimes className="me-2" />
              Cerrar
            </button>
            
            <button 
              type="button" 
              className="btn btn-success"
              onClick={exportToExcel}
              disabled={loading || stats.total === 0}
              title="Exportar a Excel (CSV)"
            >
              <FaFileExcel className="me-2" />
              Exportar Excel
            </button>
            
            <button 
              type="button" 
              className="btn btn-outline-primary"
              onClick={printReport}
              disabled={loading || stats.total === 0}
            >
              <FaPrint className="me-2" />
              Imprimir
            </button>
            
            <button 
              type="button" 
              className="btn btn-danger"
              onClick={generatePDF}
              disabled={loading || stats.total === 0}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Generando PDF...
                </>
              ) : (
                <>
                  <FaDownload className="me-2" />
                  Descargar PDF
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PDFLowStockReport;