import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../services/api";
import { generatePDF } from "./generatePDF";
import { 
  FaPrint, 
  FaArrowLeft,
  FaCheckCircle,
  FaTimesCircle,
  FaFileInvoiceDollar
} from "react-icons/fa";

const InvoiceDetail = () => {
  const { id } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [client, setClient] = useState(null);

  useEffect(() => {
    const fetchInvoice = async () => {
      try {
        const response = await api.get(`invoices/${id}/`);
        setInvoice(response.data);
        
        // Obtener detalles del cliente si está disponible
        if (response.data.client) {
          const clientRes = await api.get(`clients/${response.data.client}/`);
          setClient(clientRes.data);
        }
      } catch (err) {
        console.error("Error al cargar factura:", err);
        setError("No se pudo cargar la factura. Por favor intente nuevamente.");
      } finally {
        setLoading(false);
      }
    };

    fetchInvoice();
  }, [id]);

  const handlePrint = () => {
    if (invoice) {
      generatePDF({
        ...invoice,
        clientName: client?.name || "Cliente no especificado",
        clientId: client?.id || "N/A"
      });
    }
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center mt-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Cargando...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger mt-4" role="alert">
        {error}
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="alert alert-warning mt-4" role="alert">
        Factura no encontrada
      </div>
    );
  }

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <Link to="/invoices" className="btn btn-outline-secondary">
          <FaArrowLeft className="me-2" /> Volver a Facturas
        </Link>
        
        <button onClick={handlePrint} className="btn btn-primary">
          <FaPrint className="me-2" /> Imprimir Factura
        </button>
      </div>

      <div className="card shadow-sm">
        <div className="card-header bg-primary text-white">
          <h4 className="mb-0">
            <FaFileInvoiceDollar className="me-2" />
            Detalle de Factura #{invoice.id}
          </h4>
        </div>
        
        <div className="card-body">
          <div className="row mb-4">
            <div className="col-md-6">
              <h5>Información del Cliente</h5>
              <p className="mb-1">
                <strong>Nombre:</strong> {client?.name || "No especificado"}
              </p>
              <p className="mb-1">
                <strong>Identificación:</strong> {client?.identification || "N/A"}
              </p>
              <p className="mb-1">
                <strong>Teléfono:</strong> {client?.phone || "N/A"}
              </p>
            </div>
            
            <div className="col-md-6 text-end">
              <h5>Información de Factura</h5>
              <p className="mb-1">
                <strong>Fecha:</strong> {new Date(invoice.created_at).toLocaleDateString()}
              </p>
              <p className="mb-1">
                <strong>Tipo:</strong> {invoice.receipt_type === 'invoice' ? 'Factura' : 'Ticket'}
              </p>
              <p className="mb-1">
                <strong>Estado:</strong>{" "}
                {invoice.status === 'completed' ? (
                  <span className="badge bg-success">
                    <FaCheckCircle className="me-1" /> Completada
                  </span>
                ) : invoice.status === 'cancelled' ? (
                  <span className="badge bg-danger">
                    <FaTimesCircle className="me-1" /> Cancelada
                  </span>
                ) : (
                  <span className="badge bg-warning text-dark">
                    {/* <FaExclamationTriangle className="me-1" /> Pendiente */}
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="table-responsive">
            <table className="table table-bordered">
              <thead className="table-light">
                <tr>
                  <th>Producto</th>
                  <th>Cantidad</th>
                  <th>Precio Unitario</th>
                  <th>Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {invoice.details.map((detail, index) => (
                  <tr key={index}>
                    <td>{detail.product_name || `Producto ${detail.product_id}`}</td>
                    <td>{detail.quantity}</td>
                    <td>${detail.price.toFixed(2)}</td>
                    <td>${(detail.quantity * detail.price).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan="3" className="text-end">
                    <strong>Total:</strong>
                  </td>
                  <td>
                    <strong>${invoice.total.toFixed(2)}</strong>
                  </td>
                </tr>
                <tr>
                  <td colSpan="3" className="text-end">
                    <strong>Efectivo Recibido:</strong>
                  </td>
                  <td>${invoice.cash_received.toFixed(2)}</td>
                </tr>
                <tr>
                  <td colSpan="3" className="text-end">
                    <strong>Cambio:</strong>
                  </td>
                  <td>${invoice.change.toFixed(2)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceDetail;