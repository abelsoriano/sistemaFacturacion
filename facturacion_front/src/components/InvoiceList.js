import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { generatePDF } from './generatePDF';
import api from "../services/api";
import { 
  FaPlus, 
  FaEye, 
  FaEdit, 
  FaTrash, 
  FaFilter, 
  FaSearch,
  FaFileInvoice,
  FaCheck,
  FaExclamationTriangle,
  FaPrint
} from "react-icons/fa";

const InvoiceList = () => {
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState([]);
  const [filteredInvoices, setFilteredInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clients, setClients] = useState({});
  const [filters, setFilters] = useState({
    status: "all", // 'all', 'pending', 'completed', 'cancelled'
    dateFrom: "",
    dateTo: "",
    client: "",
    searchTerm: ""
  });

  const statusBadges = {
    pending: { class: "warning", label: "Pendiente", icon: <FaExclamationTriangle /> },
    completed: { class: "success", label: "Completada", icon: <FaCheck /> },
    cancelled: { class: "danger", label: "Cancelada", icon: <FaTrash /> }
  };

  // Cargar facturas y clientes al montar el componente
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Cargar facturas
        const invoicesResponse = await api.get("invoices/");
        setInvoices(invoicesResponse.data);
        setFilteredInvoices(invoicesResponse.data);
        
        // Cargar clientes para mostrar nombres en lugar de IDs
        const clientsResponse = await api.get("clients/");
        const clientsMap = {};
        clientsResponse.data.forEach(client => {
          clientsMap[client.id] = client.name;
        });
        setClients(clientsMap);
      } catch (err) {
        console.error("Error al cargar datos:", err);
        setError("No se pudieron cargar las facturas. Por favor intente nuevamente.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filtrar facturas cuando cambien los filtros
  useEffect(() => {
    const filterInvoices = () => {
      return invoices.filter(invoice => {
        // Filtrar por estado
        if (filters.status !== "all" && invoice.status !== filters.status) {
          return false;
        }
        
        // Filtrar por cliente
        if (filters.client && invoice.client !== filters.client) {
          return false;
        }
        
        // Filtrar por fecha desde
        if (filters.dateFrom && new Date(invoice.date) < new Date(filters.dateFrom)) {
          return false;
        }
        
        // Filtrar por fecha hasta
        if (filters.dateTo && new Date(invoice.date) > new Date(filters.dateTo)) {
          return false;
        }
        
        // Buscar término en número de factura, cliente o total
        if (filters.searchTerm) {
          const searchLower = filters.searchTerm.toLowerCase();
          const clientName = clients[invoice.client] ? clients[invoice.client].toLowerCase() : "";
          const invoiceNumber = invoice.invoice_number ? invoice.invoice_number.toLowerCase() : "";
          
          return (
            invoiceNumber.includes(searchLower) ||
            clientName.includes(searchLower) ||
            invoice.total?.toString().includes(filters.searchTerm)
          );
        }
        
        return true;
      });
    };
    
    setFilteredInvoices(filterInvoices());
  }, [filters, invoices, clients]);

  // Manejar cambios en los filtros
  const handleFilterChange = (field, value) => {
    setFilters({
      ...filters,
      [field]: value
    });
  };

  // Resetear todos los filtros
  const resetFilters = () => {
    setFilters({
      status: "all",
      dateFrom: "",
      dateTo: "",
      client: "",
      searchTerm: ""
    });
  };

  // Mostrar solo facturas pendientes
  const showPendingOnly = () => {
    setFilters({
      ...filters,
      status: "pending"
    });
  };

  // Eliminar factura
  const handleDelete = async (id) => {
    if (window.confirm("¿Está seguro que desea eliminar esta factura?")) {
      try {
        await api.delete(`invoices/${id}/`);
        setInvoices(invoices.filter(invoice => invoice.id !== id));
        alert("Factura eliminada con éxito");
      } catch (error) {
        console.error("Error al eliminar factura:", error);
        alert("Error al eliminar la factura");
      }
    }
  };

  // Cambiar estado de factura
  const handleStatusChange = async (id, newStatus) => {
    try {
      await api.patch(`invoices/${id}/`, { status: newStatus });
      // Actualizar estado en la lista local
      const updatedInvoices = invoices.map(invoice => 
        invoice.id === id ? { ...invoice, status: newStatus } : invoice
      );
      setInvoices(updatedInvoices);
      alert(`Estado de factura actualizado a: ${statusBadges[newStatus].label}`);
    } catch (error) {
      console.error("Error al cambiar estado:", error);
      alert("Error al actualizar el estado de la factura");
    }
  };
  
  // Formatear fecha
  const formatDate = (dateString) => {
    const options = { year: 'numeric', month: 'numeric', day: 'numeric' };
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
      <div className="alert alert-danger mt-4" role="alert">
        {error}
      </div>
    );
  }

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>
          <FaFileInvoice className="me-2" />
          Facturas
        </h2>
        <Link to="/create-invoice" className="btn btn-primary">
          <FaPlus className="me-2" /> Nueva Factura
        </Link>
      </div>

      {/* Filtros */}
      <div className="card shadow-sm mb-4">
        <div className="card-header bg-light">
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0">
              <FaFilter className="me-2" /> Filtros
            </h5>
            <div>
              <button
                onClick={() => navigate("/home")}
                className="btn btn-outline-secondary me-2"
              >
                Volver
              </button>
              <button
                onClick={showPendingOnly}
                className="btn btn-sm btn-warning me-2"
              >
                <FaExclamationTriangle className="me-1" /> Ver Pendientes
              </button>
              <button
                onClick={resetFilters}
                className="btn btn-sm btn-outline-secondary"
              >
                Limpiar Filtros
              </button>
            </div>
          </div>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-3">
              <label className="form-label">Estado:</label>
              <select
                className="form-select"
                value={filters.status}
                onChange={(e) => handleFilterChange("status", e.target.value)}
              >
                <option value="all">Todos</option>
                <option value="pending">Pendientes</option>
                <option value="completed">Completadas</option>
                <option value="cancelled">Canceladas</option>
              </select>
            </div>
            <div className="col-md-3">
              <label className="form-label">Cliente:</label>
              <select
                className="form-select"
                value={filters.client}
                onChange={(e) => handleFilterChange("client", e.target.value)}
              >
                <option value="">Todos</option>
                {Object.entries(clients).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-3">
              <label className="form-label">Desde:</label>
              <input
                type="date"
                className="form-control"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange("dateFrom", e.target.value)}
              />
            </div>
            <div className="col-md-3">
              <label className="form-label">Hasta:</label>
              <input
                type="date"
                className="form-control"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange("dateTo", e.target.value)}
              />
            </div>
            <div className="col-md-12">
              <div className="input-group">
                <span className="input-group-text bg-white">
                  <FaSearch />
                </span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Buscar por número, cliente o total..."
                  value={filters.searchTerm}
                  onChange={(e) =>
                    handleFilterChange("searchTerm", e.target.value)
                  }
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lista de facturas */}
      <div className="card shadow-sm">
        <div className="table-responsive">
          <table className="table table-hover mb-0">
            <thead className="table-light">
              <tr>
                <th>Nº Factura</th>
                <th>Cliente</th>
                <th>Fecha</th>
                <th>Total</th>
                <th>Estado</th>
                <th style={{ width: "200px" }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-4 text-muted">
                    No se encontraron facturas con los filtros seleccionados.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td>{invoice.invoice_number || `FACT-${invoice.id}`}</td>
                    <td>
                      {clients[invoice.client] || "Cliente no disponible"}
                    </td>
                    <td>{formatDate(invoice.date)}</td>
                    <td className="text-end">
                      $
                      {!isNaN(parseFloat(invoice.total))
                        ? parseFloat(invoice.total).toFixed(2)
                        : "0.00"}
                    </td>

                    <td>
                      <span
                        className={`badge bg-${
                          statusBadges[invoice.status]?.class || "secondary"
                        }`}
                      >
                        {statusBadges[invoice.status]?.icon}{" "}
                        {statusBadges[invoice.status]?.label || invoice.status}
                      </span>
                    </td>
                    <td>
                      <div className="btn-group">
                        <Link
                          to={`/invoice-detail/${invoice.id}`}
                          className="btn btn-sm btn-outline-primary"
                        >
                          <FaEye />
                        </Link>
                        <Link
                          to={`/edit-invoice/${invoice.id}`}
                          className="btn btn-sm btn-outline-secondary"
                        >
                          <FaEdit />
                        </Link>
                        <button
                          onClick={() =>
                            generatePDF({
                              ...invoice,
                              clientName:
                                clients[invoice.client] ||
                                "Cliente no disponible",
                            })
                          }
                          className="btn btn-sm btn-outline-dark"
                        >
                          <FaPrint />
                        </button>

                        {invoice.status === "pending" && (
                          <button
                            onClick={() =>
                              handleStatusChange(invoice.id, "completed")
                            }
                            className="btn btn-sm btn-outline-success"
                            title="Marcar como completada"
                          >
                            <FaCheck />
                          </button>
                        )}

                        <button
                          onClick={() => handleDelete(invoice.id)}
                          className="btn btn-sm btn-outline-danger"
                        >
                          <FaTrash />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Resumen */}
      <div className="card mt-4 bg-light">
        <div className="card-body py-2">
          <div className="row text-center">
            <div className="col-md-4">
              <span className="fw-bold">Total Facturas:</span>{" "}
              {filteredInvoices.length}
            </div>
            <div className="col-md-4">
              <span className="fw-bold">Pendientes:</span>{" "}
              {
                filteredInvoices.filter((inv) => inv.status === "pending")
                  .length
              }
            </div>
            <div className="col-md-4">
              <span className="fw-bold">Monto Total:</span> $
              {filteredInvoices
                .reduce((sum, invoice) => {
                  const total = parseFloat(invoice.total);
                  return sum + (isNaN(total) ? 0 : total);
                }, 0)
                .toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceList;