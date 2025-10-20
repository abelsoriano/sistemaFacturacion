import React from 'react';
import { FaFilePdf, FaPrint, FaDownload } from 'react-icons/fa';
import api from '../services/api';

const PDFLowStockReport = ({ lowStockProducts, onClose }) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const generatePDF = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.post('/reports/low-stock-pdf/', {
        products: lowStockProducts,
        date: new Date().toISOString(),
        title: 'Reporte de Productos con Bajo Stock'
      }, {
        responseType: 'blob'
      });

      // Crear URL para el blob y descargar
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      // Crear enlace para descarga
      const link = document.createElement('a');
      link.href = url;
      link.download = `productos-bajo-stock-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      
      // Limpiar
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      
      // Cerrar modal después de descargar
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

  const printReport = () => {
    const printContent = document.getElementById('report-preview');
    const windowPrint = window.open('', '', 'width=800,height=600');
    
    windowPrint.document.write(`
      <html>
        <head>
          <title>Reporte de Productos con Bajo Stock</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
          <style>
            body { padding: 20px; }
            @media print {
              .no-print { display: none; }
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
      windowPrint.close();
    }, 250);
  };

  return (
    <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header bg-danger text-white">
            <h5 className="modal-title">
              <FaFilePdf className="me-2" />
              Reporte de Productos con Bajo Stock
            </h5>
            <button 
              type="button" 
              className="btn-close btn-close-white" 
              onClick={onClose}
              disabled={loading}
            ></button>
          </div>
          
          <div className="modal-body">
            {error && (
              <div className="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error:</strong> {error}
                <button 
                  type="button" 
                  className="btn-close" 
                  onClick={() => setError(null)}
                ></button>
              </div>
            )}

            {/* Vista previa del reporte */}
            <div className="report-preview" id="report-preview">
              <div className="text-center mb-4">
                <h2 className="text-danger">Productos con Bajo Stock</h2>
                <p className="text-muted">
                  Generado el: {new Date().toLocaleDateString('es-ES', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
                <hr className="border-danger" />
              </div>

              <div className="table-responsive">
                <table className="table table-bordered table-striped">
                  <thead className="table-danger">
                    <tr>
                      <th style={{ width: '10%' }}>#</th>
                      <th style={{ width: '15%' }}>Código</th>
                      <th style={{ width: '35%' }}>Producto</th>
                      <th style={{ width: '15%' }} className="text-center">Stock Actual</th>
                      <th style={{ width: '15%' }} className="text-center">Stock Mínimo</th>
                      <th style={{ width: '10%' }} className="text-center">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowStockProducts.map((product, index) => (
                      <tr key={product.id || index}>
                        <td className="text-center">{index + 1}</td>
                        <td className="fw-bold">{product.code || `PROD-${index + 1}`}</td>
                        <td>
                          {product.name}
                          {product.description && (
                            <div>
                              <small className="text-muted">{product.description}</small>
                            </div>
                          )}
                        </td>
                        <td className="text-center">
                          <span className={`badge ${product.stock === 0 ? 'bg-danger' : 'bg-warning'}`}>
                            {product.stock} unidades
                          </span>
                        </td>
                        <td className="text-center">{product.min_stock || 3} unidades</td>
                        <td className="text-center">
                          {product.stock === 0 ? (
                            <span className="badge bg-danger">Agotado</span>
                          ) : product.stock <= (product.min_stock || 3) ? (
                            <span className="badge bg-warning">Crítico</span>
                          ) : (
                            <span className="badge bg-info">Bajo</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 p-3 bg-light rounded">
                <h6 className="text-danger">Resumen:</h6>
                <ul className="list-unstyled mb-0">
                  <li>📦 Total de productos con bajo stock: <strong>{lowStockProducts.length}</strong></li>
                  <li>❌ Productos agotados: <strong>{lowStockProducts.filter(p => p.stock === 0).length}</strong></li>
                  <li>⚠️ Productos con stock crítico: <strong>{lowStockProducts.filter(p => p.stock > 0 && p.stock <= (p.min_stock || 3)).length}</strong></li>
                </ul>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={onClose}
              disabled={loading}
            >
              Cancelar
            </button>
            <button 
              type="button" 
              className="btn btn-warning"
              onClick={printReport}
              disabled={loading}
            >
              <FaPrint className="me-2" />
              Imprimir
            </button>
            <button 
              type="button" 
              className="btn btn-danger"
              onClick={generatePDF}
              disabled={loading}
            >
              <FaDownload className="me-2" />
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Generando...
                </>
              ) : (
                'Descargar PDF'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PDFLowStockReport;