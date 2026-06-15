import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { generatePDF } from "./generatePDF";
import api from "../services/api";
import { toast, Toaster } from "react-hot-toast";
import Swal from "sweetalert2";
import "../css/facturaList.css";
import { FINANCIAL_TOTALS_PERMISSIONS, userHasAnyPermission } from '../utils/permissions';

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
  pending: { chipClass: "chip-pending", label: "Pendiente de cobro", icon: <FaExclamationTriangle size={8} /> },
  paid: { chipClass: "chip-paid", label: "Pagada", icon: <FaCheck size={8} /> },
  completed: { chipClass: "chip-completed", label: "Completada", icon: <FaCheck size={8} /> },
  cancelled: { chipClass: "chip-cancelled", label: "Cancelada", icon: <FaTimes size={8} /> },
  refunded: { chipClass: "chip-refunded", label: "Reembolsada", icon: <FaExchangeAlt size={8} /> },
};

const ECF_STATUS_CONFIG = {
  draft: { label: "Borrador", color: "#667085", bg: "#f2f4f7" },
  xml_generated: { label: "XML", color: "#175cd3", bg: "#eff8ff" },
  signed: { label: "Firmado", color: "#3538cd", bg: "#eef4ff" },
  submitted: { label: "Enviado", color: "#0e7090", bg: "#ecfdff" },
  accepted: { label: "Aceptado", color: "#067647", bg: "#ecfdf3" },
  rejected: { label: "Rechazado", color: "#b42318", bg: "#fef3f2" },
  cancelled: { label: "Anulado", color: "#475467", bg: "#f2f4f7" },
};

const JOB_STATUS_CONFIG = {
  idle: { label: "Inactivo", color: "#475467", bg: "#f2f4f7" },
  queued: { label: "En cola", color: "#175cd3", bg: "#eff8ff" },
  running: { label: "Ejecutando", color: "#6941c6", bg: "#f4f3ff" },
  retrying: { label: "Reintentando", color: "#b54708", bg: "#fffaeb" },
  failed: { label: "Fallido", color: "#b42318", bg: "#fef3f2" },
};

const FISCAL_ACTION_LOCKED_STATUSES = new Set([
  "signed",
  "submitted",
  "processing",
  "accepted",
  "rejected",
]);

const getFiscalStatus = (invoice) => invoice.fiscal_status || invoice.ecf_status || null;
const getJobStatus = (invoice) => invoice.job_status || invoice.ecf_job_status || null;
const getEffectiveFiscalStatus = (invoice) => getFiscalStatus(invoice) || "draft";
const isFiscalAcceptedPendingPayment = (invoice, fiscalStatus) => (
  invoice.status === "pending" && fiscalStatus === "accepted"
);
const canEditInvoice = (invoice) => getEffectiveFiscalStatus(invoice) === "draft";
const canDeleteInvoice = (invoice) => {
  const fiscalStatus = getFiscalStatus(invoice);
  if (!fiscalStatus) return true;
  if (FISCAL_ACTION_LOCKED_STATUSES.has(fiscalStatus)) return false;
  return fiscalStatus === "draft" && !invoice.encf && !invoice.track_id;
};
const canCreateCreditNote = (invoice) => getFiscalStatus(invoice) === "accepted";
const canCollectInvoice = (invoice) => (
  invoice.can_collect === true ||
  (
    invoice.status === "pending" &&
    !invoice.inventory_committed_at &&
    !getFiscalStatus(invoice) &&
    !invoice.encf &&
    !invoice.track_id
  )
);

const StatusBadge = ({ status, configMap, emptyLabel = "—" }) => {
  if (!status) {
    return <span className="muted-status">{emptyLabel}</span>;
  }
  const config = configMap[status] || { label: status, color: "#344054", bg: "#f2f4f7" };
  return (
    <span className="ecf-pill" style={{ color: config.color, background: config.bg }}>
      {config.label}
    </span>
  );
};

const EcfIdentity = ({ invoice }) => {
  const status = getFiscalStatus(invoice);
  if (!status) {
    return <span className="muted-status">Sin e-CF</span>;
  }
  return (
    <div className="ecf-identity">
      {invoice.encf && <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "#667085" }}>{invoice.encf}</span>}
      {invoice.track_id && <span style={{ fontSize: 10, color: "#667085" }}>TrackID listo</span>}
      {invoice.ecf_last_error && <span style={{ fontSize: 10, color: "#b42318" }}>Requiere atención</span>}
    </div>
  );
};

/* ─── Componente Principal ─────────────────────────────────────────────── */
const InvoiceList = () => {
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const canViewSalesTotals = userHasAnyPermission(currentUser, FINANCIAL_TOTALS_PERMISSIONS);
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clients, setClients] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  

  const [filters, setFilters] = useState({
    status: "all",
    fiscalStatus: "all",
    jobStatus: "all",
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

    if (filters.fiscalStatus !== "all") {
      result = result.filter(inv => getEffectiveFiscalStatus(inv) === filters.fiscalStatus);
    }

    if (filters.jobStatus !== "all") {
      result = result.filter(inv => (getJobStatus(inv) || "idle") === filters.jobStatus);
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
        const total = canViewSalesTotals ? String(inv.total) : "";
        return invNumber.includes(searchLower) || 
               clientName.includes(searchLower) || 
               total.includes(searchLower);
      });
    }

    setFiltered(result);
  }, [filters, invoices, clients, canViewSalesTotals]);

  const updateFilter = (key, value) => setFilters(prev => ({ ...prev, [key]: value }));
  const resetFilters = () => setFilters({ status: "all", fiscalStatus: "all", jobStatus: "all", dateFrom: "", dateTo: "", client: "", search: "" });
  
  const hasActiveFilters = filters.status !== "all" || 
                          filters.fiscalStatus !== "all" ||
                          filters.jobStatus !== "all" ||
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

  const handleCollectInvoice = async (invoice) => {
    const invoiceNumber = invoice.invoice_number || `FACT-${invoice.id}`;
    const result = await Swal.fire({
      title: "¿Cobrar y emitir esta factura?",
      text: `La factura #${invoiceNumber} descontará inventario y se enviará al flujo e-CF.`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#6C63FF",
      confirmButtonText: "Cobrar y emitir",
      cancelButtonText: "Cancelar"
    });

    if (result.isConfirmed) {
      try {
        const { data } = await api.post(`invoices/${invoice.id}/collect/`);
        setInvoices(prev => prev.map(i => i.id === invoice.id ? { ...i, ...data } : i));
        toast.success("Factura cobrada y enviada al flujo e-CF");
      } catch (err) {
        toast.error(err.response?.data?.detail || "No se pudo cobrar y emitir la factura");
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
            <div className="stat-label">Pendientes de cobro</div>
            <div className="stat-value warning">{pendingCount}</div>
            <div className="stat-sub">por cobrar</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Pagadas</div>
            <div className="stat-value success">{paidCount}</div>
            <div className="stat-sub">{canViewSalesTotals ? formatMoney(paidAmount) : "facturas cobradas"}</div>
          </div>
           {canViewSalesTotals && (
          <div className="stat-card">
            <div className="stat-label">Monto total</div>
            <div className="stat-value primary">{formatMoney(totalAmount)}</div>
            <div className="stat-sub">todas las facturas</div>
          </div>
          )}
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
                <label className="filter-label">Estado de pago</label>
                <div className="status-pills">
                  {[
                    ["all", "Todos"],
                    ["pending", "Pendiente de cobro"],
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

              <div className="filter-field full-width">
                <label className="filter-label">Estado fiscal e-CF</label>
                <div className="status-pills">
                  {[
                    ["all", "Todos"],
                    ["draft", "Borrador"],
                    ["xml_generated", "XML"],
                    ["signed", "Firmado"],
                    ["submitted", "Enviado"],
                    ["accepted", "Aceptado"],
                    ["rejected", "Rechazado"]
                  ].map(([val, label]) => (
                    <button
                      key={val}
                      className={`status-pill ${filters.fiscalStatus === val ? "active-all" : ""}`}
                      onClick={() => updateFilter("fiscalStatus", val)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-field full-width">
                <label className="filter-label">Proceso técnico</label>
                <div className="status-pills">
                  {[
                    ["all", "Todos"],
                    ["idle", "Inactivo"],
                    ["queued", "En cola"],
                    ["running", "Ejecutando"],
                    ["retrying", "Reintentando"],
                    ["failed", "Fallido"]
                  ].map(([val, label]) => (
                    <button
                      key={val}
                      className={`status-pill ${filters.jobStatus === val ? "active-all" : ""}`}
                      onClick={() => updateFilter("jobStatus", val)}
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
              ["pending", "Pendientes de cobro"],
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
            {canViewSalesTotals && filtered.length > 0 && (
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
                 {canViewSalesTotals &&  <th className="text-right"><FaMoneyBillWave size={10} /> Total</th>}
                  <th>Estado de pago</th>
                  <th>Fiscal e-CF</th>
                  <th>Proceso</th>
                  <th>e-NCF</th>
                  <th className="text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={canViewSalesTotals ? 9 : 8}>
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
                    const invoiceNumber = invoice.invoice_number || `FACT-${invoice.id}`;
                    const clientName = clients[invoice.client] || "Consumidor Final";
                    const showEdit = canEditInvoice(invoice);
                    const showDelete = canDeleteInvoice(invoice);
                    const showCreditNote = canCreateCreditNote(invoice);
                    const fiscalStatus = getEffectiveFiscalStatus(invoice);
                    const jobStatus = getJobStatus(invoice) || "idle";
                    const statusConfig = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.pending;
                    const showAcceptedPendingPayment = isFiscalAcceptedPendingPayment(invoice, fiscalStatus);
                    const showCollect = canCollectInvoice(invoice);
                    
                    return (
                      <tr key={invoice.id}>
                        <td data-label="Nº factura">
                          <span className="invoice-number">#{invoiceNumber}</span>
                        </td>
                        <td data-label="Cliente">
                          <span className="client-name">{clientName}</span>
                        </td>
                        <td data-label="Fecha">
                          <span className="date-text">{formatDate(invoice.date || invoice.created_at)}</span>
                          
                        </td>
                        {canViewSalesTotals &&<td data-label="Total" className="text-right">
                          <span className="total-amount">{formatMoney(invoice.total)}</span>
                        </td>}
                        <td data-label="Estado de pago">
                          <div className="payment-status-cell">
                            <span
                              className={`status-chip ${statusConfig.chipClass}`}
                              title={showAcceptedPendingPayment ? "Fiscalmente aceptada, pendiente de cobro." : statusConfig.label}
                            >
                              {statusConfig.icon} {statusConfig.label}
                            </span>
                            {showAcceptedPendingPayment && (
                              <span className="payment-status-hint">
                                Fiscalmente aceptada, pendiente de cobro
                              </span>
                            )}
                          </div>
                        </td>
                        <td data-label="Fiscal e-CF">
                          <StatusBadge status={fiscalStatus} configMap={ECF_STATUS_CONFIG} />
                        </td>
                        <td data-label="Proceso">
                          <StatusBadge status={jobStatus} configMap={JOB_STATUS_CONFIG} />
                        </td>
                        <td data-label="e-NCF">
                          <EcfIdentity invoice={invoice} />
                        </td>
                        <td data-label="Acciones" className="text-right">
                          <div className="action-buttons">
                            <div className="action-group">
                              <Link to={`/invoices/${invoice.id}`} className="action-btn btn-view" title="Ver factura">
                                <FaEye size={12} />
                              </Link>
                              {showEdit && (
                                <Link to={`/edit-invoice/${invoice.id}`} className="action-btn btn-edit" title="Editar borrador">
                                  <FaEdit size={12} />
                                </Link>
                              )}
                              <button
                                className="action-btn btn-print"
                                title="Imprimir"
                                onClick={() => generatePDF(
                                  { ...invoice, clientName },
                                  {
                                    filename: `factura_${invoice.invoice_number || invoice.id}.pdf`,
                                    showClientName: true,
                                    showNotes: true,
                                  }
                                )}
                              >
                                <FaPrint size={12} />
                              </button>
                            </div>
                            <div className="action-group">
                              {showCreditNote && (
                                <button
                                  className="action-btn btn-pay"
                                  title="Nota de crédito E34"
                                  onClick={() => navigate(`/invoices/${invoice.id}`)}
                                >
                                  <FaExchangeAlt size={12} />
                                </button>
                              )}
                              {showCollect && (
                                <button
                                  className="action-btn btn-pay"
                                  title="Cobrar y emitir e-CF"
                                  onClick={() => handleCollectInvoice(invoice)}
                                >
                                  <FaCheck size={12} />
                                </button>
                              )}
                            </div>
                            {showDelete && (
                              <div className="action-group">
                                <button
                                  className="action-btn btn-delete"
                                  title="Eliminar borrador"
                                  onClick={() => handleDelete(invoice.id, invoiceNumber)}
                                >
                                  <FaTrash size={12} />
                                </button>
                              </div>
                            )}
                            {!showEdit && !showDelete && (
                              <span className="fiscal-lock-hint">Bloqueada</span>
                            )}
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
