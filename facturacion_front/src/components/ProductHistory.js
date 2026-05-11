import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { showErrorAlert } from '../herpert';

const ProductHistory = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [productName, setProductName] = useState('');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const response = await api.get(`products/${id}/history/`);
        setHistory(response.data);

        if (response.data.length > 0) {
          setProductName(response.data[0].product_name);
        } else {
          const productResponse = await api.get(`products/${id}/`);
          setProductName(productResponse.data.name);
        }
      } catch (error) {
        console.error('Error fetching product history:', error);
        showErrorAlert('Error', 'No se pudo cargar el historial del producto.');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [id]);

  const formatChangedFields = (changedFields) => {
    if (!changedFields) return 'Sin cambios detallados';

    return Object.entries(changedFields).map(([key, values]) => {
      if (typeof values === 'object') {
        return (
          <div key={key} className="mb-2">
            <strong>{key.replace('_', ' ')}:</strong>
            <div className="ms-3">
              <div><strong>Anterior:</strong> {values.old ?? 'N/A'}</div>
              <div><strong>Nuevo:</strong> {values.new ?? 'N/A'}</div>
            </div>
          </div>
        );
      }

      return (
        <div key={key} className="mb-2">
          <strong>{key.replace('_', ' ')}:</strong> {values}
        </div>
      );
    });
  };

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2>Historial de Producto</h2>
          <p className="text-muted mb-0">{productName ? `Registro de cambios para ${productName}` : 'Registro de cambios del producto'}</p>
        </div>
        <button className="btn btn-outline-secondary" onClick={() => navigate('/productsList')}>
          ← Volver a productos
        </button>
      </div>

      {loading ? (
        <div className="d-flex justify-content-center align-items-center py-5">
          <div className="spinner-border text-primary me-3" role="status">
            <span className="visually-hidden">Cargando...</span>
          </div>
          <span>Cargando historial...</span>
        </div>
      ) : history.length === 0 ? (
        <div className="alert alert-info">
          No hay registros de historial disponibles para este producto.
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-hover align-middle">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Acción</th>
                <th>Detalles</th>
                <th>Nota</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.id}>
                  <td>{new Date(entry.timestamp).toLocaleString()}</td>
                  <td className="text-capitalize">{entry.action}</td>
                  <td>{formatChangedFields(entry.changed_fields)}</td>
                  <td>{entry.note || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ProductHistory;
