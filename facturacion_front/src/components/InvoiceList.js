import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { generatePDF } from "./generatePDF";
import api from "../services/api";
import { toast, Toaster } from "react-hot-toast";
import Swal from "sweetalert2";
import "../css/facturaList.css";

import {
  FaPlus,
  FaEye,
  FaEdit,
  FaTrash,
  FaSearch,
  FaFileInvoice,
  FaCheck,
  FaExclamationTriangle,
  FaPrint,
  FaTimes,
  FaExchangeAlt,
  FaArrowLeft,
  FaFilter,
  FaSlidersH,
  FaMoneyBillWave,
  FaCalendarAlt,
  FaUser,
  FaHashtag
} from "react-icons/fa";

/* ─── Helpers ──────────────────────────────────────────────────────────── */
const formatMoney = (n) => `$${(+n || 0).toFixed(2)}`;
const formatDate = (dateStr) => {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("es-ES", {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
};

const STATUS_CONFIG = {
  pending: { chipClass: "chip-pending", label: "Pendiente", icon: <FaExclamationTriangle size={8} /> },
  paid: { chipClass: "chip-paid", label: "Pagada", icon: <FaCheck size={8} /> },
  completed: { chipClass: "chip-completed", label: "Completada", icon: <FaCheck size={8} /> },
  cancelled: { chipClass: "chip-cancelled", label: "Cancelada", icon: <FaTimes size={8} /> },
  refunded: { chipClass: "chip-refunded", label: "Reembolsada", icon: <FaExchangeAlt size={8} /> },
};

/* ─── Componente Principal ─────────────────────────────────────────────── */
const InvoiceList = () => {
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clients, setClients] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    status: "all",
    dateFrom: "",
    dateTo: "",
    client: "",
    search: ""
  });

  // Cargar datos
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [invoicesRes, clientsRes] = await Promise.all([
          api.get("invoices/"),
          api.get("clients/")
        ]);
        setInvoices(invoicesRes.data);
        setFiltered(invoicesRes.data);
        
        const clientMap = {};
        clientsRes.data.forEach(c => { clientMap[c.id] = c.name; });
        setClients(clientMap);
      } catch (err) {
        setError("Error al cargar las facturas");
        toast.error("Error al cargar datos");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // Filtrar
  useEffect(() => {
    let result = [...invoices];

    if (filters.status !== "all") {
      result = result.filter(inv => inv.status === filters.status);
    }

    if (filters.client) {
      result = result.filter(inv => String(inv.client) === String(filters.client));
    }

    if (filters.dateFrom) {
      result = result.filter(inv => new Date(inv.date) >= new Date(filters.dateFrom));
    }

    if (filters.dateTo) {
      result = result.filter(inv => new Date(inv.date) <= new Date(filters.dateTo));
    }

    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      result = result.filter(inv => {
        const clientName = (clients[inv.client] || "").toLowerCase();
        const invNumber = (inv.invoice_number || `FACT-${inv.id}`).toLowerCase();
        const total = String(inv.total);
        return invNumber.includes(searchLower) || 
               clientName.includes(searchLower) || 
               total.includes(searchLower);
      });
    }

    setFiltered(result);
  }, [filters, invoices, clients]);

  const updateFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value }));
  const resetFilters = () => setFilters({ status: "all", dateFrom: "", dateTo: "", client: "", search: "" });
  
  const hasActiveFilters = filters.status !== "all" || 
                          filters.dateFrom || 
                          filters.dateTo || 
                          filters.client || 
                          filters.search;

  // Acciones
  const handleDelete = async (id, invoiceNum) => {
    const result = await Swal.fire({
      title: "¿Eliminar factura?",
      text: `La factura #${invoiceNum} será eliminada permanentemente.`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#ef4444",
      confirmButtonText: "Eliminar",
      cancelButtonText: "Cancelar"
    });

    if (result.isConfirmed) {
      try {
        await api.delete(`invoices/${id}/`);
        setInvoices(prev => prev.filter(i => i.id !== id));
        toast.success("Factura eliminada");
      } catch {
        toast.error("Error al eliminar");
      }
    }
  };

  const handleStatusChange = async (id, newStatus) => {
    const config = STATUS_CONFIG[newStatus];
    const result = await Swal.fire({
      title: `¿Marcar como ${config?.label || newStatus}?`,
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: "#3b82f6",
      confirmButtonText: "Confirmar"
    });

    if (result.isConfirmed) {
      try {
        await api.patch(`invoices/${id}/`, { status: newStatus });
        setInvoices(prev => prev.map(i => i.id === id ? { ...i, status: newStatus } : i));
        toast.success(`Estado actualizado a ${config?.label}`);
      } catch {
        toast.error("Error al actualizar");
      }
    }
  };

  // Estadísticas
  const totalAmount = invoices.reduce((sum, inv) => sum + (parseFloat(inv.total) || 0), 0);
  const pendingCount = invoices.filter(i => i.status === "pending").length;
  const paidCount = invoices.filter(i => i.status === "paid" || i.status === "completed").length;
  const paidAmount = invoices.filter(i => i.status === "paid" || i.status === "completed")
    .reduce((sum, inv) => sum + (parseFloat(inv.total) || 0), 0);

  // Estados de carga y error
  if (loading) {
    return (
      <div className="lst-root">
        <div className="state-center">
          <div className="spinner" />
          <span style={{ color: "var(--text-muted)" }}>Cargando facturas...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="lst-root">
        <div className="state-center">
          <FaExclamationTriangle size={32} style={{ color: "var(--danger)", opacity: 0.6 }} />
          <span style={{ color: "var(--text-muted)" }}>{error}</span>
          <button className="btn-outline" onClick={() => window.location.reload()}>
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="lst-root">
      <Toaster position="top-right" />

      {/* Header */}
      <header className="lst-header">
        <button className="btn-outline" onClick={() => navigate("/home")}>
          <FaArrowLeft size={12} /> Volver
        </button>

        <div className="lst-header-title">
          <FaFileInvoice size={16} />
          Facturas
          <span className="badge">{invoices.length}</span>
        </div>

        <div className="lst-header-actions">
          <button
            className={`btn-outline ${showFilters ? "btn-primary" : ""}`}
            onClick={() => setShowFilters(!showFilters)}
            style={showFilters ? { background: "var(--primary)", color: "white", borderColor: "var(--primary)" } : {}}
          >
            <FaSlidersH size={12} /> Filtros
            {hasActiveFilters && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--primary)", display: "inline-block" }} />}
          </button>
          <Link to="/create-invoice" className="btn-primary">
            <FaPlus size={12} /> Nueva factura
          </Link>
        </div>
      </header>

      <div className="lst-body">
        {/* Stats */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Total facturas</div>
            <div className="stat-value primary">{invoices.length}</div>
            <div className="stat-sub">{filtered.length} en vista</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Pendientes</div>
            <div className="stat-value warning">{pendingCount}</div>
            <div className="stat-sub">por cobrar</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Pagadas</div>
            <div className="stat-value success">{paidCount}</div>
            <div className="stat-sub">{formatMoney(paidAmount)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Monto total</div>
            <div className="stat-value primary">{formatMoney(totalAmount)}</div>
            <div className="stat-sub">todas las facturas</div>
          </div>
        </div>

        {/* Panel de filtros avanzados */}
        {showFilters && (
          <div className="filter-panel">
            <div className="filter-header">
              <div className="filter-title">
                <FaFilter size={12} /> Filtros avanzados
                {hasActiveFilters && (
                  <span className="badge" style={{ background: "var(--primary-light)", color: "var(--primary)" }}>
                    activos
                  </span>
                )}
              </div>
              {hasActiveFilters && (
                <button className="btn-clear" onClick={resetFilters}>
                  <FaTimes size={10} /> Limpiar todo
                </button>
              )}
            </div>
            <div className="filter-body">
              <div className="filter-field full-width">
                <label className="filter-label">Estado</label>
                <div className="status-pills">
                  {[
                    ["all", "Todos"],
                    ["pending", "Pendiente"],
                    ["paid", "Pagada"],
                    ["completed", "Completada"],
                    ["cancelled", "Cancelada"],
                    ["refunded", "Reembolsada"]
                  ].map(([val, label]) => (
                    <button
                      key={val}
                      className={`status-pill ${filters.status === val ? `active-${val}` : ""}`}
                      onClick={() => updateFilter("status", val)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-field">
                <label className="filter-label"><FaUser size={10} /> Cliente</label>
                <select
                  className="filter-select"
                  value={filters.client}
                  onChange={(e) => updateFilter("client", e.target.value)}
                >
                  <option value="">Todos los clientes</option>
                  {Object.entries(clients).map(([id, name]) => (
                    <option key={id} value={id}>{name}</option>
                  ))}
                </select>
              </div>

              <div className="filter-field">
                <label className="filter-label"><FaCalendarAlt size={10} /> Desde</label>
                <input
                  type="date"
                  className="filter-input"
                  value={filters.dateFrom}
                  onChange={(e) => updateFilter("dateFrom", e.target.value)}
                />
              </div>

              <div className="filter-field">
                <label className="filter-label"><FaCalendarAlt size={10} /> Hasta</label>
                <input
                  type="date"
                  className="filter-input"
                  value={filters.dateTo}
                  onChange={(e) => updateFilter("dateTo", e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* Barra de búsqueda rápida */}
        <div className="search-bar">
          <FaSearch className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por número, cliente o monto..."
            value={filters.search}
            onChange={(e) => updateFilter("search", e.target.value)}
          />
          {filters.search && (
            <button className="clear-search" onClick={() => updateFilter("search", "")}>
              <FaTimes size={12} />
            </button>
          )}
        </div>

        {/* Filtros rápidos cuando el panel está cerrado */}
        {!showFilters && (
          <div className="status-pills" style={{ marginBottom: "1rem" }}>
            {[
              ["all", "Todos"],
              ["pending", "Pendientes"],
              ["paid", "Pagadas"],
              ["cancelled", "Canceladas"]
            ].map(([val, label]) => (
              <button
                key={val}
                className={`status-pill ${filters.status === val ? `active-${val}` : ""}`}
                onClick={() => updateFilter("status", val)}
              >
                {label}
                {val !== "all" && (
                  <span style={{ fontSize: 10, fontFamily: "var(--mono)" }}>
                    ({invoices.filter(i => i.status === val).length})
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Tabla de facturas */}
        <div className="table-container">
          <div className="table-header">
            <div className="table-title">
              Resultados
              <span className="badge">{filtered.length}</span>
            </div>
            {filtered.length > 0 && (
              <span style={{ fontSize: "0.75rem", color: "var(--text-faint)", fontFamily: "var(--mono)" }}>
                Total: {formatMoney(filtered.reduce((sum, inv) => sum + (parseFloat(inv.total) || 0), 0))}
              </span>
            )}
          </div>

          <div className="responsive-table">
            <table className="invoice-table">
              <thead>
                <tr>
                  <th><FaHashtag size={10} /> Nº factura</th>
                  <th><FaUser size={10} /> Cliente</th>
                  <th><FaCalendarAlt size={10} /> Fecha</th>
                  <th className="text-right"><FaMoneyBillWave size={10} /> Total</th>
                  <th>Estado</th>
                  <th className="text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan="6">
                      <div className="empty-state">
                        <FaFileInvoice size={48} />
                        <p>
                          {hasActiveFilters
                            ? "No hay resultados con los filtros actuales"
                            : "No hay facturas registradas"}
                        </p>
                        {hasActiveFilters && (
                          <button className="btn-outline" style={{ marginTop: "0.75rem" }} onClick={resetFilters}>
                            Limpiar filtros
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ) : (
                  filtered.map(invoice => {
                    const statusConfig = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.pending;
                    const invoiceNumber = invoice.invoice_number || `FACT-${invoice.id}`;
                    const clientName = clients[invoice.client] || "—";
                    
                    return (
                      <tr key={invoice.id}>
                        <td>
                          <span className="invoice-number">#{invoiceNumber}</span>
                        </td>
                        <td>
                          <span className="client-name">{clientName}</span>
                        </td>
                        <td>
                          <span className="date-text">{formatDate(invoice.date || invoice.created_at)}</span>
                          
                        </td>
                        <td className="text-right">
                          <span className="total-amount">{formatMoney(invoice.total)}</span>
                        </td>
                        <td>
                          <span className={`status-chip ${statusConfig.chipClass}`}>
                            {statusConfig.icon} {statusConfig.label}
                          </span>
                        </td>
                        <td className="text-right">
                          <div className="action-buttons">
                            <Link to={`/invoices/${invoice.id}`} className="action-btn btn-view" title="Ver">
                              <FaEye size={12} />
                            </Link>
                            <Link to={`/edit-invoice/${invoice.id}`} className="action-btn btn-edit" title="Editar">
                              <FaEdit size={12} />
                            </Link>
                            <button
                              className="action-btn btn-print"
                              title="Imprimir"
                              onClick={() => generatePDF({ ...invoice, clientName })}
                            >
                              <FaPrint size={12} />
                            </button>
                            {invoice.status === "pending" && (
                              <button
                                className="action-btn btn-pay"
                                title="Marcar como pagada"
                                onClick={() => handleStatusChange(invoice.id, "paid")}
                              >
                                <FaCheck size={12} />
                              </button>
                            )}
                            <button
                              className="action-btn btn-delete"
                              title="Eliminar"
                              onClick={() => handleDelete(invoice.id, invoiceNumber)}
                            >
                              <FaTrash size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceList;