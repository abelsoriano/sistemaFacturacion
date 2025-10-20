import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import { 
  FaArrowLeft, 
  FaEdit, 
  FaPrint, 
  FaCheck, 
  FaTimes, 
  FaExclamationTriangle,
  FaFileInvoice,
  FaUser,
  FaCalendar,
  FaHashtag
} from "react-icons/fa";

const InvoiceDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [client, setClient] = useState(null);
  const [products, setProducts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const statusBadges = {
    pending: { 
      class: "warning", 
      label: "Pendiente", 
      icon: <FaExclamationTriangle />,
      bgClass: "bg-warning-subtle"
    },
    completed: { 
      class: "success", 
      label: "Completada", 
      icon: <FaCheck />,
      bgClass: "bg-success-subtle"
    },
    cancelled: { 
      class: "danger", 
      label: "Cancelada", 
      icon: <FaTimes />,
      bgClass: "bg-danger-subtle"
    }
  };

  useEffect(() => {
    const fetchInvoiceDetail = async () => {
      setLoading(true);
      try {
        // Cargar datos de la factura
        const invoiceResponse = await api.get(`invoices/${id}/`);
        const invoiceData = invoiceResponse.data;
        setInvoice(invoiceData);
        
        

        // Cargar datos del cliente
        if (invoiceData.client) {
          const clientResponse = await api.get(`clients/${invoiceData.client}/`);
          setClient(clientResponse.data);
        }

        // Cargar productos para mostrar nombres
        const productsResponse = await api.get("products/");
        const productsMap = {};
        productsResponse.data.forEach(product => {
          productsMap[product.id] = product;
        });
        setProducts(productsMap);

      } catch (err) {
        console.error("Error al cargar detalles de la factura:", err);
        setError("No se pudo cargar la información de la factura.");
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchInvoiceDetail();
    }
  }, [id]);
  console.log("Factura cargada:", invoice);

  // Cambiar estado de la factura
  const handleStatusChange = async (newStatus) => {
    try {
      await api.patch(`invoices/${id}/`, { status: newStatus });
      setInvoice({ ...invoice, status: newStatus });
      alert(`Factura marcada como ${statusBadges[newStatus].label}`);
    } catch (error) {
      console.error("Error al cambiar estado:", error);
      alert("Error al actualizar el estado de la factura");
    }
  };

  // Eliminar factura
  const handleDelete = async () => {
    if (window.confirm("¿Está seguro que desea eliminar esta factura? Esta acción no se puede deshacer.")) {
      try {
        await api.delete(`invoices/${id}/`);
        alert("Factura eliminada con éxito");
        navigate("/invoices");
      } catch (error) {
        console.error("Error al eliminar factura:", error);
        alert("Error al eliminar la factura");
      }
    }
  };

  // Manejar impresión
  const handlePrint = () => {
    window.print();
  };

  // Formatear fecha
  const formatDate = (dateString) => {
    const options = { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      weekday: 'long'
    };
    return new Date(dateString).toLocaleDateString('es-ES', options);
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
      <div className="container mt-4">
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
        <Link to="/invoices" className="btn btn-secondary">
          <FaArrowLeft className="me-2" /> Volver a Facturas
        </Link>
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="container mt-4">
        <div className="alert alert-warning" role="alert">
          Factura no encontrada.
        </div>
        <Link to="/invoices" className="btn btn-secondary">
          <FaArrowLeft className="me-2" /> Volver a Facturas
        </Link>
      </div>
    );
  }
  

  const statusInfo = statusBadges[invoice.status] || statusBadges.pending;
  const total = invoice.total || invoice.details?.reduce((sum, detail) => sum + (detail.quantity * detail.price), 0) || 0;

  return (
    <div className="container py-4">
      {/* Encabezado */}
      <div className="d-flex justify-content-between align-items-center mb-4 no-print">
        <div>
          <h2 className="mb-1">
            <FaFileInvoice className="me-2" />
            Factura #{invoice.invoice_number || `FACT-${invoice.id}`}
          </h2>
          <p className="text-muted mb-0">Detalle completo de la factura</p>
        </div>
        <div className="btn-group">
          <Link to="/invoice-list" className="btn btn-outline-secondary">
            <FaArrowLeft className="me-2" /> Volver
          </Link>
          <Link to={`/edit-invoice/${id}`} className="btn btn-outline-primary">
            <FaEdit className="me-2" /> Editar
          </Link>
          <button onClick={handlePrint} className="btn btn-outline-dark">
            <FaPrint className="me-2" /> Imprimir
          </button>
          {invoice.status === "pending" && (
            <button
              onClick={() => handleStatusChange("completed")}
              className="btn btn-success"
            >
              <FaCheck className="me-2" /> Completar
            </button>
          )}
          {invoice.status !== "cancelled" && (
            <button
              onClick={() => handleStatusChange("cancelled")}
              className="btn btn-outline-warning"
            >
              <FaTimes className="me-2" /> Cancelar
            </button>
          )}
        </div>
      </div>

      {/* Información de la factura */}
      <div className="row mb-4">
        <div className="col-md-8">
          <div className="card shadow-sm">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Información de la Factura</h5>
              <span className={`badge bg-${statusInfo.class} fs-6`}>
                {statusInfo.icon} {statusInfo.label}
              </span>
            </div>
            <div className="card-body">
              <div className="row">
                <div className="col-md-6">
                  <div className="mb-3">
                    <label className="form-label text-muted">
                      <FaHashtag className="me-2" />
                      Número de Factura:
                    </label>
                    <p className="fw-bold">
                      {invoice.invoice_number || `FACT-${invoice.id}`}
                    </p>
                  </div>
                  <div className="mb-3">
                    <label className="form-label text-muted">
                      <FaCalendar className="me-2" />
                      Fecha:
                    </label>
                    <p className="fw-bold">{formatDate(invoice.date)}</p>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="mb-3">
                    <label className="form-label text-muted">Estado:</label>
                    <div className={`p-3 rounded ${statusInfo.bgClass}`}>
                      <span className={`badge bg-${statusInfo.class} me-2`}>
                        {statusInfo.icon}
                      </span>
                      {statusInfo.label}
                    </div>
                  </div>
                </div>
              </div>
              {invoice.notes && (
                <div className="mt-3">
                  <label className="form-label text-muted">Notas:</label>
                  <div className="bg-light p-3 rounded">{invoice.notes}</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Información del cliente */}
        <div className="col-md-4">
          <div className="card shadow-sm">
            <div className="card-header">
              <h5 className="mb-0">
                <FaUser className="me-2" />
                Cliente
              </h5>
            </div>
            <div className="card-body">
              {client ? (
                <div>
                  <h6 className="fw-bold">{client.name}</h6>
                  {client.email && (
                    <p className="mb-1">
                      <small className="text-muted">Email:</small>
                      <br />
                      {client.email}
                    </p>
                  )}
                  {client.phone && (
                    <p className="mb-1">
                      <small className="text-muted">Teléfono:</small>
                      <br />
                      {client.phone}
                    </p>
                  )}
                  {client.address && (
                    <p className="mb-1">
                      <small className="text-muted">Dirección:</small>
                      <br />
                      {client.address}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-muted">
                  Información del cliente no disponible
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Detalles de la factura */}
      <div className="card shadow-sm mb-4">
        <div className="card-header">
          <h5 className="mb-0">Detalles de la Factura</h5>
        </div>
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover mb-0">
              <thead className="table-light">
                <tr>
                  <th>Producto</th>
                  <th className="text-center">Cantidad</th>
                  <th className="text-end">Precio Unitario</th>
                  <th className="text-end">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {invoice.details && invoice.details.length > 0 ? (
                  invoice.details.map((detail, index) => (
                    <tr key={index}>
                      <td>
                        <div>
                          <strong>
                            {detail.product_name || "Producto no disponible"}
                          </strong>
                          {detail.product_description && (
                            <div className="text-muted small">
                              {detail.product_description}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="text-center">{detail.quantity}</td>
                      <td className="text-end">
                        {detail.price != null &&
                        !isNaN(parseFloat(detail.price))
                          ? `$${parseFloat(detail.price).toFixed(2)}`
                          : "0.00"}
                      </td>
                      <td className="text-end fw-bold">
                        $
                        {(detail.quantity * parseFloat(detail.price)).toFixed(
                          2
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="text-center py-4 text-muted">
                      No hay detalles disponibles para esta factura.
                    </td>
                  </tr>
                )}
              </tbody>
              <tfoot className="table-light">
                <tr>
                  <td colSpan="3" className="text-end fw-bold fs-5">
                    Total:
                  </td>
                  <td className="text-end fw-bold fs-5 text-primary">
                    $
                    {!isNaN(parseFloat(total))
                      ? parseFloat(total).toFixed(2)
                      : "0.00"}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>

      {/* Acciones adicionales */}
      <div className="row no-print">
        <div className="col-md-12">
          <div className="card bg-light">
            <div className="card-body">
              <h6 className="card-title">Acciones Adicionales</h6>
              <div className="btn-group">
                {invoice.status === "pending" && (
                  <button
                    onClick={() => handleStatusChange("completed")}
                    className="btn btn-success"
                  >
                    <FaCheck className="me-2" /> Marcar como Completada
                  </button>
                )}
                {invoice.status === "completed" && (
                  <button
                    onClick={() => handleStatusChange("pending")}
                    className="btn btn-warning"
                  >
                    <FaExclamationTriangle className="me-2" /> Marcar como
                    Pendiente
                  </button>
                )}
                <button onClick={handleDelete} className="btn btn-danger">
                  <FaTimes className="me-2" /> Eliminar Factura
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Estilos para impresión */}
      <style jsx>{`
        @media print {
          .no-print {
            display: none !important;
          }
          .container {
            max-width: none !important;
            margin: 0 !important;
            padding: 20px !important;
          }
          .card {
            border: 1px solid #ddd !important;
            box-shadow: none !important;
          }
          .card-header {
            background-color: #f8f9fa !important;
            border-bottom: 1px solid #ddd !important;
          }
          body {
            font-size: 12px !important;
          }
        }
      `}</style>
    </div>
  );
};

export default InvoiceDetail;