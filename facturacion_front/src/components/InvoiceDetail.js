import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import { toast, Toaster } from "react-hot-toast";
import Swal from "sweetalert2";
import { getSavedPDFConfig, PDF_DEFAULT_CONFIG } from "../utils/pdfConfig";
import "../css/detalleVenta.css";
import logo from "../logo.png"; // ajusta la ruta
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
  FaHashtag,
  FaMoneyBillWave,
  FaCreditCard,
  FaExchangeAlt,
  FaBox,
  FaTrash,
  FaBarcode,
  FaStickyNote,
  FaReceipt,
  FaPhone,
  FaEnvelope,
  FaMapMarkerAlt,
  FaIdCard,
  FaLock
} from "react-icons/fa";




/* ─── Helpers ──────────────────────────────────────────────────────────── */
const formatMoney = (n) => `$${(+n || 0).toFixed(2)}`;

const formatDate = (dateString) => {
  if (!dateString) return "—";
  return new Date(dateString).toLocaleDateString("es-ES", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
};

const getInitials = (name = "") =>
  name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2) || "?";

const STATUS_CONFIG = {
  pending: { chipClass: "chip-pending", label: "Pendiente de cobro", icon: <FaExclamationTriangle size={8} /> },
  paid: { chipClass: "chip-paid", label: "Pagada", icon: <FaCheck size={8} /> },
  cancelled: { chipClass: "chip-cancelled", label: "Cancelada", icon: <FaTimes size={8} /> },
  refunded: { chipClass: "chip-refunded", label: "Reembolsada", icon: <FaExchangeAlt size={8} /> },
};

const ECF_STATUS_CONFIG = {
  draft: { label: "Borrador", color: "#667085", bg: "#f2f4f7" },
  xml_generated: { label: "XML generado", color: "#175cd3", bg: "#eff8ff" },
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

const StatusPill = ({ status, configMap, emptyLabel = "Sin e-CF" }) => {
  if (!status) return <span className="det-muted-pill">{emptyLabel}</span>;
  const config = configMap[status] || { label: status, color: "#344054", bg: "#f2f4f7" };
  return (
    <span className="det-status-pill" style={{ color: config.color, background: config.bg }}>
      {config.label}
    </span>
  );
};

const PAYMENT_CONFIG = {
  cash: { cls: "pay-cash", label: "Efectivo", icon: <FaMoneyBillWave size={12} /> },
  card: { cls: "pay-card", label: "Tarjeta", icon: <FaCreditCard size={12} /> },
  transfer: { cls: "pay-transfer", label: "Transferencia", icon: <FaExchangeAlt size={12} /> },
};

const FISCAL_ACTION_LOCKED_STATUSES = new Set([
  "signed",
  "submitted",
  "processing",
  "accepted",
  "rejected",
]);

const canCollectInvoice = (invoice, fiscalStatus) => (
  invoice?.can_collect === true ||
  (
    invoice?.status === "pending" &&
    !invoice?.inventory_committed_at &&
    !fiscalStatus &&
    !invoice?.encf &&
    !invoice?.track_id
  )
);

/* ─── Componente Principal ─────────────────────────────────────────────── */
const InvoiceDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isPrinting, setIsPrinting] = useState(false);
  const [companyInfo, setCompanyInfo] = useState(PDF_DEFAULT_CONFIG.company);

  useEffect(() => {
    const savedConfig = getSavedPDFConfig();
    if (savedConfig.company) {
      setCompanyInfo({ ...PDF_DEFAULT_CONFIG.company, ...savedConfig.company });
    }
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`invoices/${id}/`);
        setInvoice(data);
        
        if (data.client) {
          try {
            const { data: clientData } = await api.get(`clients/${data.client}/`);
            setClient(clientData);
          } catch {
            // Cliente no encontrado
          }
        }
      } catch {
        setError("No se pudo cargar la información de la factura.");
        toast.error("Error al cargar la factura");
      } finally {
        setLoading(false);
      }
    };
    
    if (id) fetchData();
    const intervalId = window.setInterval(() => {
      if (id) fetchData();
    }, 15000);
    return () => window.clearInterval(intervalId);
  }, [id]);

  const handleStatusChange = async (newStatus) => {
    const config = STATUS_CONFIG[newStatus];
    const result = await Swal.fire({
      title: `¿Marcar como ${config?.label || newStatus}?`,
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: newStatus === "cancelled" ? "#ef4444" : "#3b82f6",
      confirmButtonText: "Confirmar",
      cancelButtonText: "Cancelar"
    });
    
    if (result.isConfirmed) {
      try {
        await api.patch(`invoices/${id}/`, { status: newStatus });
        setInvoice({ ...invoice, status: newStatus });
        toast.success(`Estado actualizado a ${config?.label || newStatus}`);
      } catch {
        toast.error("Error al actualizar el estado");
      }
    }
  };

  const handleCollect = async () => {
    const result = await Swal.fire({
      title: "¿Cobrar y emitir esta factura?",
      text: "Se descontará inventario y se enviará al flujo e-CF. Esta operación no debe repetirse.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#6C63FF",
      confirmButtonText: "Cobrar y emitir",
      cancelButtonText: "Cancelar"
    });

    if (result.isConfirmed) {
      try {
        const { data } = await api.post(`invoices/${id}/collect/`);
        setInvoice(data);
        toast.success("Factura cobrada y enviada al flujo e-CF");
      } catch (err) {
        toast.error(err.response?.data?.detail || "No se pudo cobrar y emitir la factura");
      }
    }
  };

  const handleDelete = async () => {
    if (!canDeleteInvoice) {
      toast.error("Factura bloqueada fiscalmente. Usa nota de crédito si aplica.");
      return;
    }
    const result = await Swal.fire({
      title: "¿Eliminar factura?",
      text: "Esta acción no se puede deshacer.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#ef4444",
      confirmButtonText: "Sí, eliminar",
      cancelButtonText: "Cancelar"
    });
    
    if (result.isConfirmed) {
      try {
        await api.delete(`invoices/${id}/`);
        toast.success("Factura eliminada");
        navigate("/invoice-list");
      } catch {
        toast.error("Error al eliminar la factura");
      }
    }
  };

  const handleCreditNote = async () => {
    const result = await Swal.fire({
      title: "Emitir nota de crédito E34",
      input: "textarea",
      inputLabel: "Motivo fiscal",
      inputPlaceholder: "Describe el motivo del reverso...",
      inputValidator: (value) => !value ? "El motivo fiscal es requerido" : undefined,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Emitir E34",
      cancelButtonText: "Cancelar"
    });

    if (result.isConfirmed) {
      try {
        const { data } = await api.post("credit-notes/", {
          origin_invoice: invoice.id,
          reason: result.value
        });
        const fiscalStatus = data.fiscal_status || data.ecf_status || "draft";
        const jobStatus = data.job_status || data.ecf_job_status || "idle";
        const queueLabel = data.ecf_enqueued ? "Pipeline e-CF en cola" : "Pipeline e-CF no encolado";
        const inventoryStatus = data.inventory_reconciliation_status || "restored_pending";
        const reviewLabel = data.requires_manual_review ? " Requiere revisión manual." : "";
        toast.success(`E34 creada: ${data.encf || data.credit_note_number}. ${queueLabel}. Fiscal: ${fiscalStatus}. Proceso: ${jobStatus}. Inventario: ${inventoryStatus}.${reviewLabel}`);
        if (data.ecf_error) {
          toast.error(data.ecf_error);
        }
      } catch (err) {
        toast.error(err.response?.data?.detail || "No se pudo crear la nota de crédito");
      }
    }
  };

  const handlePrint = () => {
    setIsPrinting(true);
    setTimeout(() => {
      window.print();
      setIsPrinting(false);
    }, 100);
  };

  // Estados de carga y error
  if (loading) {
    return (
      <div className="det-root">
        <div className="state-center">
          <div className="spinner" />
          <span className="meta-value">Cargando factura...</span>
        </div>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="det-root">
        <div className="state-center">
          <FaExclamationTriangle size={32} style={{ color: "var(--danger)", opacity: 0.6 }} />
          <span className="meta-value">{error || "Factura no encontrada"}</span>
          <button className="btn btn-outline" onClick={() => navigate("/invoice-list")}>
            <FaArrowLeft size={12} /> Volver a facturas
          </button>
        </div>
      </div>
    );
  }

  // Valores calculados
  const total = parseFloat(invoice.total || invoice.details?.reduce((s, d) => s + d.quantity * parseFloat(d.price || 0), 0) || 0);
  const tax = parseFloat(invoice.tax || 0);
  const discount = parseFloat(invoice.discount || 0);
  const subtotal = parseFloat(invoice.subtotal || (total - tax + discount));
  const change = parseFloat(invoice.change || 0);
  const cashReceived = parseFloat(invoice.cash_received || 0);
  const statusInfo = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.pending;
  const paymentInfo = PAYMENT_CONFIG[invoice.payment_method] || PAYMENT_CONFIG.cash;
  const invoiceNumber = invoice.invoice_number || `FACT-${invoice.id}`;
  const fiscalLocked = Boolean(invoice.is_fiscally_locked);
  const fiscalStatus = invoice.fiscal_status || invoice.ecf_status || null;
  const jobStatus = invoice.job_status || invoice.ecf_job_status || "idle";
  const effectiveFiscalStatus = fiscalStatus || "draft";
  const canEditInvoice = effectiveFiscalStatus === "draft";
  const canDeleteInvoice = !fiscalStatus || (effectiveFiscalStatus === "draft" && !invoice.encf && !invoice.track_id);
  const canIssueCreditNote = effectiveFiscalStatus === "accepted";
  const isFiscalActionLocked = fiscalLocked || FISCAL_ACTION_LOCKED_STATUSES.has(effectiveFiscalStatus);
  const canCollect = canCollectInvoice(invoice, fiscalStatus);

  return (
    <div className="det-root">
      <Toaster position="top-right" />

      {/* Header */}
      <header className="det-header no-print">
        <button className="btn btn-outline btn-sm" onClick={() => navigate("/invoice-list")}>
          <FaArrowLeft size={12} /> Volver
        </button>

        <div className="det-header-title">
          <FaFileInvoice size={14} style={{ color: "var(--primary)" }} />
          Factura
          <span className="det-invoice-num">#{invoiceNumber}</span>
          <span className={`status-chip ${statusInfo.chipClass}`}>
            {statusInfo.icon} {statusInfo.label}
          </span>
          <StatusPill status={fiscalStatus} configMap={ECF_STATUS_CONFIG} />
          <StatusPill status={jobStatus} configMap={JOB_STATUS_CONFIG} emptyLabel="Inactivo" />
          {fiscalLocked && (
            <span className="status-chip chip-cancelled">
              <FaLock size={8} /> Bloqueo fiscal
            </span>
          )}
        </div>

        <div className="det-header-actions">
          <button className="btn btn-outline btn-sm" onClick={handlePrint} disabled={isPrinting}>
            <FaPrint size={11} /> {isPrinting ? "Preparando..." : "Imprimir"}
          </button>
          {canEditInvoice && (
            <Link to={`/edit-invoice/${id}`} className="btn btn-outline btn-sm">
              <FaEdit size={11} /> Editar
            </Link>
          )}
          {canCollect && (
            <button className="btn btn-success btn-sm" onClick={handleCollect}>
              <FaCheck size={11} /> Cobrar y emitir
            </button>
          )}
        </div>
      </header>

      <div className="print-only" style={{  textAlign: "center",   padding: "1.25rem 0 0.75rem" }}>
        <div style={{display: "flex", alignItems: "center", justifyContent: "center", gap: "10px"}}> 
        <img src={logo} alt="Logo"  className="hd-logo" style={{height: "45px",  width: "auto"}}></img>
          <h2 style={{ fontSize: "1.25rem",  fontWeight: 700,  margin: 0  }}>
            FACTURA #{invoiceNumber}
          </h2>
        </div>

        <p style={{fontSize: "0.75rem",  color: "#666",  marginTop: "0.25rem" }}>
          {companyInfo.name} · {companyInfo.address} · {companyInfo.phone}
        </p>

        <hr style={{ margin: "0.75rem 0" }} />
      </div>

      {/* Body */}
      <div className="det-body">
        {/* Columna izquierda - Información principal */}
        <div>
          {/* Información de la factura */}
          <div className="det-card">
            <div className="det-card-header">
              <span className="det-card-title">
                <FaFileInvoice size={12} /> Información de la factura
              </span>
              <span className={`status-chip ${statusInfo.chipClass}`}>
                {statusInfo.icon} {statusInfo.label}
              </span>
            </div>
            <div className="det-card-body">
              <div className="meta-grid">
                <div className="meta-item">
                  <div className="meta-label"><FaHashtag size={9} /> Número</div>
                  <div className="meta-value mono">#{invoiceNumber}</div>
                </div>
                <div className="meta-item">
                  <div className="meta-label"><FaCalendar size={9} /> Fecha de emisión</div>
                  <div className="meta-value">{formatDate(invoice.date || invoice.created_at)}</div>
                </div>
                <div className="meta-item">
                  <div className="meta-label"><FaMoneyBillWave size={9} /> Método de pago</div>
                  <div className="meta-value">
                    <span className={`pay-badge ${paymentInfo.cls}`}>
                      {paymentInfo.icon} {paymentInfo.label}
                    </span>
                  </div>
                </div>
                <div className="meta-item">
                  <div className="meta-label"><FaReceipt size={9} /> Tipo</div>
                  <div className="meta-value">
                    {invoice.receipt_type === "invoice" ? "Factura" : "Ticket"}
                  </div>
                </div>
                {invoice.origin_quotation_number && (
                  <div className="meta-item">
                    <div className="meta-label"><FaFileInvoice size={9} /> Cotización origen</div>
                    <div className="meta-value mono">{invoice.origin_quotation_number}</div>
                  </div>
                )}
              </div>

              {invoice.notes && (
                <>
                  <div className="divider" />
                  <div className="notes-box">
                    <FaStickyNote size={14} />
                    <span>{invoice.notes}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="det-card">
            <div className="det-card-header">
              <span className="det-card-title">
                <FaReceipt size={12} /> e-CF / DGII
              </span>
              <div className="det-status-cluster">
                <StatusPill status={fiscalStatus} configMap={ECF_STATUS_CONFIG} />
                <StatusPill status={jobStatus} configMap={JOB_STATUS_CONFIG} emptyLabel="Inactivo" />
              </div>
            </div>
            <div className="det-card-body">
              <div className="det-section-note">
                <strong>Factura comercial</strong> y <strong>validación fiscal DGII</strong> se muestran por separado para evitar cambios operativos sobre documentos cerrados.
              </div>
              <div className="meta-grid">
                <div className="meta-item">
                  <div className="meta-label"><FaReceipt size={9} /> Estado fiscal</div>
                  <div className="meta-value">
                    <StatusPill status={fiscalStatus} configMap={ECF_STATUS_CONFIG} />
                  </div>
                </div>
                <div className="meta-item">
                  <div className="meta-label"><FaExchangeAlt size={9} /> Proceso técnico</div>
                  <div className="meta-value">
                    <StatusPill status={jobStatus} configMap={JOB_STATUS_CONFIG} emptyLabel="Inactivo" />
                  </div>
                </div>
                <div className="meta-item">
                  <div className="meta-label"><FaHashtag size={9} /> e-NCF</div>
                  <div className="meta-value mono">{invoice.encf || "Pendiente"}</div>
                </div>
                <div className="meta-item">
                  <div className="meta-label"><FaReceipt size={9} /> TrackID</div>
                  <div className="meta-value mono">{invoice.track_id || "Pendiente DGII"}</div>
                </div>
              </div>
              {invoice.ecf_last_error && (
                <>
                  <div className="divider" />
                  <div className="notes-box" style={{ color: "#b42318", background: "#fef3f2" }}>
                    <FaExclamationTriangle size={14} />
                    <span>{invoice.ecf_last_error}</span>
                  </div>
                </>
              )}
              {fiscalLocked && (
                <>
                  <div className="divider" />
                  <div className="notes-box" style={{ color: "#b54708", background: "#fffaeb" }}>
                    <FaLock size={14} />
                    <span>{invoice.fiscal_lock_reason || "Documento protegido. Los cambios se realizan mediante nota de crédito E34."}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Productos */}
          <div className="det-card">
            <div className="det-card-header">
              <span className="det-card-title">
                <FaBox size={12} /> Productos
                {invoice.details?.length > 0 && (
                  <span className="det-invoice-num" style={{ background: "var(--primary-light)", color: "var(--primary)" }}>
                    {invoice.details.length} ítems
                  </span>
                )}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-faint)" }}>
                {invoice.details?.reduce((s, d) => s + (d.quantity || 0), 0)} unidades
              </span>
            </div>

            {!invoice.details?.length ? (
              <div className="empty-products">
                <FaBox size={40} />
                <p>Sin productos registrados</p>
              </div>
            ) : (
              <>
                <div className="table-wrapper">
                  <table className="prod-table">
                    <thead>
                      <tr>
                        <th style={{ width: 48 }}>#</th>
                        <th>Descripción</th>
                        <th className="center" style={{ width: 80 }}>Cant.</th>
                        <th className="right" style={{ width: 100 }}>Precio</th>
                        <th className="right" style={{ width: 110 }}>Subtotal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoice.details.map((detail, idx) => {
                        const price = parseFloat(detail.price || 0);
                        const quantity = parseInt(detail.quantity || 0);
                        const subtotalItem = price * quantity;
                        const productName = detail.product_name || detail.product?.name || `Producto #${detail.product || detail.product_id}`;
                        
                        return (
                          <tr key={idx}>
                            <td><div className="prod-idx">{idx + 1}</div></td>
                            <td>
                              <div className="prod-name">{productName}</div>
                              {detail.barcode && (
                                <div className="prod-barcode">
                                  <FaBarcode size={9} style={{ marginRight: 3 }} />{detail.barcode}
                                </div>
                              )}
                            </td>
                            <td className="center">
                              <div className="prod-qty">{quantity}</div>
                            </td>
                            <td className="right">
                              <div className="prod-price">{formatMoney(price)}</div>
                            </td>
                            <td className="right">
                              <div className="prod-subtotal">{formatMoney(subtotalItem)}</div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="totals-footer">
                  <div className="totals-row muted">
                    <span>Subtotal</span>
                    <span className="amt-mono">{formatMoney(subtotal)}</span>
                  </div>
                  {discount > 0 && (
                    <div className="totals-row discount">
                      <span>Descuento</span>
                      <span className="amt-mono">−{formatMoney(discount)}</span>
                    </div>
                  )}
                  <div className="totals-row muted">
                    <span>IVA</span>
                    <span className="amt-mono">{formatMoney(tax)}</span>
                  </div>
                  <div className="totals-row final">
                    <span>Total</span>
                    <span className="amt">{formatMoney(total)}</span>
                  </div>

                  {cashReceived > 0 && (
                    <div className="cash-box">
                      <div className="cash-box-row">
                        <span style={{ color: "var(--text-muted)" }}>Efectivo recibido</span>
                        <span className="amt-mono" style={{ fontWeight: 600 }}>{formatMoney(cashReceived)}</span>
                      </div>
                      <div className="change-strip">
                        <span className="lbl">Cambio</span>
                        <span className="amt">{formatMoney(change)}</span>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Columna derecha - Panel de acciones */}
        <div className="panel-stack no-print">
          {/* Cliente */}
          <div className="det-card">
            <div className="det-card-header">
              <span className="det-card-title"><FaUser size={12} /> Cliente</span>
            </div>
            <div className="det-card-body">
              {client ? (
                <>
                  <div className="client-header">
                    <div className="client-avatar">{getInitials(client.name)}</div>
                    <div className="client-info">
                      <div className="client-name">{client.name}</div>
                      {client.ruc_ci && (
                        <div className="client-doc">
                          <FaIdCard size={9} style={{ marginRight: 4 }} />{client.ruc_ci}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {client.email && (
                    <div className="client-detail-row">
                      <span className="client-detail-label"><FaEnvelope size={10} /> Email</span>
                      <span className="client-detail-value">{client.email}</span>
                    </div>
                  )}
                  {client.phone && (
                    <div className="client-detail-row">
                      <span className="client-detail-label"><FaPhone size={10} /> Teléfono</span>
                      <span className="client-detail-value">{client.phone}</span>
                    </div>
                  )}
                  {client.address && (
                    <div className="client-detail-row">
                      <span className="client-detail-label"><FaMapMarkerAlt size={10} /> Dirección</span>
                      <span className="client-detail-value">{client.address}</span>
                    </div>
                  )}
                </>
              ) : (
                <div style={{ textAlign: "center", padding: "1rem 0", color: "var(--text-faint)" }}>
                  <FaUser size={28} style={{ opacity: 0.3, marginBottom: "0.5rem" }} />
                  <div>Consumidor final</div>
                </div>
              )}
            </div>
          </div>

          {/* Resumen de pago */}
          <div className="det-card">
            <div className="det-card-header">
              <span className="det-card-title">Resumen de pago</span>
            </div>
            <div className="det-card-body">
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>Método de pago</span>
                <span className={`pay-badge ${paymentInfo.cls}`}>
                  {paymentInfo.icon} {paymentInfo.label}
                </span>
              </div>
              
              <div className="divider" />
              
              <div style={{ marginTop: "0.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "0.375rem 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                  <span>Subtotal</span>
                  <span className="amt-mono">{formatMoney(subtotal)}</span>
                </div>
                {discount > 0 && (
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "0.375rem 0", fontSize: "0.8125rem", color: "var(--success)" }}>
                    <span>Descuento</span>
                    <span className="amt-mono">−{formatMoney(discount)}</span>
                  </div>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", padding: "0.375rem 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                  <span>IVA</span>
                  <span className="amt-mono">{formatMoney(tax)}</span>
                </div>
              </div>
              
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.75rem", paddingTop: "0.75rem", borderTop: "2px solid var(--border)" }}>
                <span style={{ fontWeight: 700, fontSize: "1rem" }}>Total</span>
                <span style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: "1.25rem", color: "var(--primary)" }}>{formatMoney(total)}</span>
              </div>
              
              {cashReceived > 0 && (
                <div className="cash-box" style={{ marginTop: "0.75rem" }}>
                  <div className="cash-box-row">
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Efectivo recibido</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: "0.8125rem", fontWeight: 600 }}>{formatMoney(cashReceived)}</span>
                  </div>
                  <div className="change-strip" style={{ marginTop: "0.5rem" }}>
                    <span className="lbl">Cambio</span>
                    <span className="amt">{formatMoney(change)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Acciones */}
          <div className="det-card">
            <div className="det-card-header">
              <span className="det-card-title">Acciones</span>
            </div>
            <div className="det-card-body">
              <div className="actions-panel">
                <div className="action-section-label">Comercial</div>
                {canCollect && (
                  <button className="btn btn-success action-btn-full" onClick={handleCollect}>
                    <FaCheck size={11} /> Cobrar y emitir
                  </button>
                )}
                {invoice.status === "paid" && !isFiscalActionLocked && (
                  <button className="btn btn-info action-btn-full" onClick={() => handleStatusChange("refunded")}>
                    <FaExchangeAlt size={11} /> Reembolsar
                  </button>
                )}
                {invoice.status !== "cancelled" && invoice.status !== "paid" && !isFiscalActionLocked && (
                  <button className="btn btn-danger action-btn-full" onClick={() => handleStatusChange("cancelled")}>
                    <FaTimes size={11} /> Anular factura
                  </button>
                )}
                {canEditInvoice && (
                  <Link to={`/edit-invoice/${id}`} className="btn btn-outline action-btn-full">
                    <FaEdit size={11} /> Editar factura
                  </Link>
                )}
                {isFiscalActionLocked && (
                  <div className="det-action-hint">
                    <FaLock size={11} /> Las acciones comerciales directas están bloqueadas por el estado fiscal.
                  </div>
                )}

                <div className="divider" />

                <div className="action-section-label">Fiscal</div>
                {canIssueCreditNote && (
                  <button className="btn btn-info action-btn-full" onClick={handleCreditNote}>
                    <FaExchangeAlt size={11} /> Nota de crédito E34
                  </button>
                )}
                {!canIssueCreditNote && (
                  <div className="det-action-hint">
                    Nota E34 disponible solo cuando DGII acepta la factura.
                  </div>
                )}
                
                <div className="divider" />

                <div className="action-section-label">Documento</div>
                <button className="btn btn-outline action-btn-full" onClick={handlePrint} disabled={isPrinting}>
                  <FaPrint size={11} /> {isPrinting ? "Preparando..." : "Imprimir"}
                </button>
                
                {canDeleteInvoice && (
                  <button className="btn btn-danger-outline action-btn-full" onClick={handleDelete}>
                    <FaTrash size={11} /> Eliminar factura
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceDetail;
