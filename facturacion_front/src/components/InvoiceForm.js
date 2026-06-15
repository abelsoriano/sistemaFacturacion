import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import {
    FaSave, FaPlus, FaTrash, FaArrowLeft, FaPrint, FaCheck,
    FaSearch, FaBarcode, FaRegFilePdf,
    FaMoneyBillWave, FaCreditCard, FaExchangeAlt,
    FaUser, FaBox, FaCalculator, FaTimes, FaTag,
    FaLock
} from "react-icons/fa";
import { toast, Toaster } from "react-hot-toast";
import Swal from "sweetalert2";
import "../css/facturaForm.css";


const INVOICE_EDIT_LOCKED_FISCAL_STATUSES = new Set([
    "signed",
    "submitted",
    "processing",
    "accepted",
    "rejected",
]);

const getFiscalStatus = (invoice) => invoice.fiscal_status || invoice.ecf_status || "draft";
const moneyNumber = (value) => Number((Number(value) || 0).toFixed(2));

/* Componente principal */
const InvoiceForm = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [clients, setClients] = useState([]);
    const [products, setProducts] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");
    const taxRate = 18;
    const [discount, setDiscount] = useState({ value: 0, type: "percentage" });
    const [applyItbis, setApplyItbis] = useState(true);
    const barcodeRef = useRef(null);

    const [invoice, setInvoice] = useState({
        client: "",
        details: [],
        status: "pending",
        date: new Date().toISOString().split("T")[0],
        notes: "",
        payment_method: "cash",
        cash_received: 0
    });

    const [errors, setErrors] = useState({});
    const fiscalStatus = getFiscalStatus(invoice);
    const fiscalLocked = Boolean(invoice.is_fiscally_locked) || INVOICE_EDIT_LOCKED_FISCAL_STATUSES.has(fiscalStatus);
    const editAccessBlocked = Boolean(id && !loading && fiscalStatus !== "draft");

    // Cargar datos iniciales
    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            try {
                const [clientsRes, productsRes] = await Promise.all([
                    api.get("clients/"),
                    api.get("products/")
                ]);
                setClients(clientsRes.data);
                setProducts(productsRes.data);

                if (id) {
                    const invRes = await api.get(`invoices/${id}/`);
                    const data = invRes.data;
                    if (data.details) {
                        data.details = data.details.map(d => ({
                            product: d.product || d.product_id,
                            product_name: d.product_name,
                            quantity: d.quantity,
                            price: parseFloat(d.price),
                            subtotal: parseFloat(d.subtotal),
                            barcode: d.barcode
                        }));
                    }
                    setInvoice(data);
                    setApplyItbis(Number(data.tax || 0) > 0);
                    if (data.discount) setDiscount({ value: data.discount, type: "percentage" });
                }
            } catch (err) {
                toast.error("Error al cargar datos");
            } finally {
                setLoading(false);
            }
        };
        loadData();
        setTimeout(() => barcodeRef.current?.focus(), 300);
    }, [id]);

    // Cálculo de totales
    const totals = useCallback(() => {
        const subtotal = moneyNumber(invoice.details.reduce((sum, d) => sum + (d.subtotal || d.quantity * d.price), 0));
        const rawDiscount = discount.type === "percentage" ? subtotal * (discount.value / 100) : discount.value;
        const discountAmount = moneyNumber(Math.min(rawDiscount, subtotal));
        const afterDiscount = moneyNumber(subtotal - discountAmount);
        const tax = moneyNumber(applyItbis ? afterDiscount * (taxRate / 100) : 0);
        const total = moneyNumber(afterDiscount + tax);
        const change = moneyNumber(invoice.payment_method === "cash" ? Math.max(0, invoice.cash_received - total) : 0);
        return { subtotal, discountAmount, tax, total, change };
    }, [invoice.details, discount, taxRate, applyItbis, invoice.payment_method, invoice.cash_received]);

    const { subtotal, discountAmount, tax, total, change } = totals();

    // Agregar producto con escáner
    const handleScan = async (barcode) => {
        if (!barcode || barcode.length < 2) return;
        setLoading(true);
        try {
            const res = await api.get(`products/search-barcode/?barcode=${barcode}`);
            addProduct(res.data);
            toast.success(`${res.data.name} agregado`);
            if (barcodeRef.current) {
                barcodeRef.current.value = "";
                barcodeRef.current.focus();
            }
        } catch {
            toast.error("Producto no encontrado");
        } finally {
            setLoading(false);
        }
    };

    const addProduct = (product, qty = 1) => {
        const exists = invoice.details.findIndex(d => d.product === product.id);
        if (exists !== -1) {
            const updated = [...invoice.details];
            updated[exists].quantity += qty;
            updated[exists].subtotal = updated[exists].quantity * updated[exists].price;
            setInvoice({ ...invoice, details: updated });
        } else {
            setInvoice({
                ...invoice,
                details: [...invoice.details, {
                    product: product.id,
                    product_name: product.name,
                    quantity: qty,
                    price: parseFloat(product.price),
                    subtotal: qty * parseFloat(product.price),
                    barcode: product.barcode
                }]
            });
        }
    };

    const updateDetail = (index, field, val) => {
        const updated = [...invoice.details];
        if (field === "quantity") {
            val = Math.max(1, parseInt(val) || 1);
            updated[index].quantity = val;
            updated[index].subtotal = val * updated[index].price;
        } else if (field === "price") {
            val = parseFloat(val) || 0;
            updated[index].price = val;
            updated[index].subtotal = updated[index].quantity * val;
        }
        setInvoice({ ...invoice, details: updated });
    };

    const removeDetail = (index, name) => {
        Swal.fire({
            title: "Eliminar producto",
            text: `¿Quitar ${name} del carrito?`,
            icon: "question",
            showCancelButton: true,
            confirmButtonColor: "#ef4444",
            confirmButtonText: "Eliminar"
        }).then(res => {
            if (res.isConfirmed) {
                setInvoice({ ...invoice, details: invoice.details.filter((_, i) => i !== index) });
                toast.success("Producto eliminado");
            }
        });
    };

    const validate = () => {
        const err = {};
        if (!invoice.client) err.client = "Seleccione un cliente";
        if (invoice.details.length === 0) err.details = "Agregue al menos un producto";
        if (invoice.payment_method === "cash" && invoice.cash_received < total)
            err.cash = `Faltan $${(total - invoice.cash_received).toFixed(2)}`;
        setErrors(err);
        return Object.keys(err).length === 0;
    };

    const submit = async (e, action = "save") => {
        if (e) e.preventDefault();
        if (!validate()) {
            toast.error("Complete los campos requeridos");
            return;
        }
        if (fiscalLocked) {
            toast.error("Factura bloqueada fiscalmente. Usa nota de crédito.");
            return;
        }
        setLoading(true);
        const data = {
            client_id: parseInt(invoice.client),
            receipt_type: "invoice",
            payment_method: invoice.payment_method,
            cash_received: moneyNumber(invoice.cash_received),
            discount: moneyNumber(discountAmount),
            apply_itbis: applyItbis,
            subtotal: moneyNumber(subtotal),
            tax: moneyNumber(tax),
            total: moneyNumber(total),
            change: moneyNumber(change),
            notes: invoice.notes,
            date: invoice.date,
            status: invoice.status,
            details: invoice.details.map(d => ({ product: d.product, quantity: d.quantity, price: moneyNumber(d.price) }))
        };
        try {
            let res;
            if (id) {
                res = await api.put(`invoices/${id}/`, data);
                toast.success("Factura actualizada");
            } else {
                res = await api.post("invoices/", data);
                toast.success("Factura guardada como pendiente. Cobra y emite cuando confirmes el pago.");
            }
            if (action === "new") {
                setInvoice({ client: "", details: [], status: "pending", date: new Date().toISOString().split("T")[0], notes: "", payment_method: "cash", cash_received: 0 });
                setDiscount({ value: 0, type: "percentage" });
                setApplyItbis(true);
                barcodeRef.current?.focus();
            } else {
                navigate(`/invoices/${res.data.id}`);
            }
        } catch (err) {
            toast.error("Error al guardar");
        } finally {
            setLoading(false);
        }
    };

    const changeStatus = async (status) => {
        const result = await Swal.fire({
            title: status === "paid" ? "¿Cobrar y emitir esta factura?" : "¿Marcar como cancelada?",
            text: status === "paid" ? "Se descontará inventario y se enviará al flujo e-CF." : undefined,
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: status === "paid" ? "Cobrar y emitir" : "Confirmar"
        });
        if (result.isConfirmed) {
            try {
                if (status === "paid") {
                    const { data } = await api.post(`invoices/${id}/collect/`);
                    setInvoice({ ...invoice, ...data });
                    toast.success("Factura cobrada y enviada al flujo e-CF");
                } else {
                    await api.patch(`invoices/${id}/`, { status });
                    setInvoice({ ...invoice, status });
                    toast.success("Estado actualizado a cancelada");
                }
            } catch (err) {
                toast.error(err.response?.data?.detail || "Error al actualizar");
            }
        }
    };

    const selectedClient = clients.find(c => String(c.id) === String(invoice.client));
    const fmt = (n) => `$${(+n || 0).toFixed(2)}`;
    const totalUnits = invoice.details.reduce((s, d) => s + d.quantity, 0);
    const filteredProducts = products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()) || p.barcode?.includes(searchTerm));

    if (editAccessBlocked) {
        return (
            <div className="inv-root">
                <Toaster position="top-right" />
                <header className="inv-page-header">
                    <div>
                        <span className="inv-eyebrow">Factura fiscal</span>
                        <h1>Factura bloqueada</h1>
                        <p>Esta factura no permite edición comercial por su estado fiscal actual.</p>
                    </div>
                    <button className="inv-btn secondary" onClick={() => navigate("/invoice-list")}>
                        <FaArrowLeft /> Volver
                    </button>
                </header>
                <section className="inv-locked-card">
                    <div className="inv-card">
                        <div className="inv-card-header">
                            <span><FaLock /> Edición no permitida</span>
                            {invoice.invoice_number && <strong>#{invoice.invoice_number}</strong>}
                        </div>
                        <div className="inv-card-body">
                            <div className="inv-warning-box">
                                Esta factura no puede editarse porque su estado fiscal es "{fiscalStatus}".
                            </div>
                            <p className="inv-muted-text">
                                Solo se permite editar facturas en estado fiscal draft. Si la factura fue firmada, enviada, aceptada o rechazada, cualquier corrección debe gestionarse por el flujo fiscal correspondiente.
                            </p>
                            <div className="inv-action-row">
                                <button className="inv-btn secondary" onClick={() => navigate("/invoice-list")}>
                                    <FaArrowLeft /> Volver a facturas
                                </button>
                                <button className="inv-btn primary" onClick={() => navigate(`/invoices/${id}`)}>
                                    Ver detalle
                                </button>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        );
    }

    return (
        <div className="inv-root">
            <Toaster position="top-right" />

            <header className="inv-page-header">
                <button className="inv-btn secondary" onClick={() => navigate("/invoice-list")}>
                    <FaArrowLeft /> Volver
                </button>

                <div className="inv-title-block">
                    <span className="inv-eyebrow">Facturación</span>
                    <h1>{id ? "Editar factura" : "Nueva factura"}</h1>
                    <div className="inv-title-meta">
                        {id && invoice.invoice_number && <span className="inv-mono">#{invoice.invoice_number}</span>}
                        {id && (
                            <span className={`status-badge status-${invoice.status === "pending" ? "pending" : invoice.status === "paid" ? "paid" : "cancelled"}`}>
                                {invoice.status === "pending" ? "Pendiente de cobro" : invoice.status === "paid" ? "Pagada" : "Cancelada"}
                            </span>
                        )}
                        {fiscalLocked && (
                            <span className="status-badge status-cancelled">
                                <FaLock size={10} /> Bloqueo fiscal
                            </span>
                        )}
                    </div>
                </div>

                <div className="inv-header-actions">
                    {id && (
                        <button className="inv-btn secondary" onClick={() => window.open(`/invoice-print/${id}`, "_blank")}>
                            <FaPrint /> Imprimir
                        </button>
                    )}
                    {id && invoice.status === "pending" && !fiscalLocked && !invoice.inventory_committed_at && !invoice.encf && (
                        <button className="inv-btn primary" onClick={() => changeStatus("paid")}>
                            <FaCheck /> Cobrar y emitir
                        </button>
                    )}
                    {id && invoice.status !== "cancelled" && !fiscalLocked && (
                        <button className="inv-btn danger" onClick={() => changeStatus("cancelled")}>
                            <FaTimes /> Cancelar
                        </button>
                    )}
                </div>
            </header>

            <section className="inv-scan-card">
                <div>
                    <span>Entrada rápida</span>
                    <strong>Escanear producto</strong>
                </div>
                <div className="inv-input-icon">
                    <FaBarcode />
                    <input
                        ref={barcodeRef}
                        type="text"
                        placeholder="Escanear código de barras..."
                        onKeyPress={(e) => e.key === "Enter" && handleScan(e.target.value)}
                        disabled={fiscalLocked}
                    />
                </div>
            </section>

            <div className="inv-grid">
                <main className="inv-main-column">
                    <section className="inv-card">
                        {fiscalLocked && (
                            <div className="inv-warning-strip">
                                <FaLock /> {invoice.fiscal_lock_reason || "Esta factura tiene bloqueo fiscal. No se puede editar."}
                            </div>
                        )}
                        <div className="inv-card-header">
                            <span><FaBox /> Productos</span>
                            <button className="inv-btn primary small" onClick={() => setShowModal(true)} disabled={fiscalLocked}>
                                <FaPlus /> Buscar producto
                            </button>
                        </div>

                        {errors.details && <div className="inv-error-box">⚠️ {errors.details}</div>}

                        {invoice.details.length === 0 ? (
                            <div className="cart-empty">
                                <FaBox className="inv-empty-icon" />
                                <p>Escanea un código o busca un producto</p>
                            </div>
                        ) : (
                            <div className="cart-table-container">
                                <table className="cart-table">
                                    <thead>
                                        <tr>
                                            <th>Producto</th>
                                            <th className="w-qty">Cant.</th>
                                            <th className="w-price">Precio</th>
                                            <th className="text-right w-subtotal">Subtotal</th>
                                            <th className="w-action"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {invoice.details.map((item, idx) => (
                                            <tr key={idx}>
                                                <td data-label="Producto">
                                                    <div className="inv-product-name">{item.product_name}</div>
                                                    {item.barcode && (
                                                        <div className="inv-product-code">
                                                            <FaBarcode />{item.barcode}
                                                        </div>
                                                    )}
                                                </td>
                                                <td data-label="Cant.">
                                                    <input
                                                        type="number"
                                                        className="qty-input"
                                                        min="1"
                                                        value={item.quantity}
                                                        onChange={(e) => updateDetail(idx, "quantity", e.target.value)}
                                                        disabled={fiscalLocked}
                                                    />
                                                </td>
                                                <td data-label="Precio">
                                                    <input
                                                        type="number"
                                                        className="price-input"
                                                        step="0.01"
                                                        value={item.price}
                                                        onChange={(e) => updateDetail(idx, "price", e.target.value)}
                                                        disabled={fiscalLocked}
                                                    />
                                                </td>
                                                <td data-label="Subtotal" className="text-right inv-mono strong">{fmt(item.subtotal)}</td>
                                                <td data-label="Acción">
                                                    <button type="button" className="inv-btn danger icon-only" onClick={() => removeDetail(idx, item.product_name)} disabled={fiscalLocked}>
                                                        <FaTrash />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                <div className="inv-cart-summary">
                                    <span>{totalUnits} unidades</span>
                                    <span>Subtotal: <strong className="inv-mono">{fmt(subtotal)}</strong></span>
                                </div>
                            </div>
                        )}
                    </section>

                    <section className="inv-card">
                        <div className="inv-card-header">
                            <span><FaTag /> Notas</span>
                        </div>
                        <div className="inv-card-body">
                            <textarea
                                placeholder="Notas adicionales para el cliente..."
                                rows="4"
                                value={invoice.notes}
                                onChange={(e) => setInvoice({ ...invoice, notes: e.target.value })}
                                disabled={fiscalLocked}
                            />
                        </div>
                    </section>
                </main>

                <aside className="inv-side-column">
                    <section className="inv-card">
                        <div className="inv-card-header">
                            <span><FaUser /> Cliente</span>
                        </div>
                        <div className="inv-card-body">
                            <select
                                className={errors.client ? "is-error" : ""}
                                value={invoice.client}
                                onChange={(e) => setInvoice({ ...invoice, client: e.target.value })}
                                disabled={fiscalLocked}
                            >
                                <option value="">Seleccionar cliente...</option>
                                {clients.map(c => (
                                    <option key={c.id} value={c.id}>{c.name} {c.ruc_ci ? `(${c.ruc_ci})` : ""}</option>
                                ))}
                            </select>
                            {errors.client && <div className="error-text"><FaTimes size={10} /> {errors.client}</div>}
                            {selectedClient && (
                                <div className="inv-client-info">
                                    {selectedClient.email && <span>{selectedClient.email}</span>}
                                    {selectedClient.phone && <span>{selectedClient.phone}</span>}
                                </div>
                            )}
                        </div>
                    </section>

                    <section className="inv-card">
                        <div className="inv-card-header">
                            <span><FaRegFilePdf /> Tipo / estado comercial</span>
                        </div>
                        <div className="inv-card-body inv-status-grid">
                            <label>
                                <span>Fecha</span>
                                <input
                                    type="date"
                                    value={invoice.date || ""}
                                    onChange={(e) => setInvoice({ ...invoice, date: e.target.value })}
                                    disabled={fiscalLocked}
                                />
                            </label>
                            {id ? (
                                <label>
                                    <span>Estado</span>
                                    <select
                                        value={invoice.status}
                                        onChange={(e) => setInvoice({ ...invoice, status: e.target.value })}
                                        disabled={fiscalLocked}
                                    >
                                        <option value="pending">Pendiente de cobro</option>
                                        <option value="paid">Pagada</option>
                                        <option value="cancelled">Cancelada</option>
                                    </select>
                                </label>
                            ) : (
                                <div className="inv-status-note">
                                    <strong>Estado inicial: pendiente de cobro</strong>
                                    <span>Guardar esta factura no descuenta inventario ni emite e-CF. Usa “Cobrar y emitir” desde el detalle cuando confirmes el pago.</span>
                                </div>
                            )}
                        </div>
                    </section>

                    <section className="inv-card">
                        <div className="inv-card-header">
                            <span><FaCalculator /> Totales</span>
                        </div>
                        <div className="inv-card-body">
                            <label className="inv-field">
                                <span><FaTag /> Descuento</span>
                                <div className="inv-discount-row">
                                    <input
                                        type="number"
                                        value={discount.value}
                                        onChange={(e) => setDiscount({ ...discount, value: parseFloat(e.target.value) || 0 })}
                                        disabled={fiscalLocked}
                                    />
                                    <button type="button" className={`inv-btn small ${discount.type === "percentage" ? "primary" : "secondary"}`} onClick={() => setDiscount({ ...discount, type: "percentage" })} disabled={fiscalLocked}>%</button>
                                    <button type="button" className={`inv-btn small ${discount.type === "fixed" ? "primary" : "secondary"}`} onClick={() => setDiscount({ ...discount, type: "fixed" })} disabled={fiscalLocked}>$</button>
                                </div>
                            </label>

                            <div className="inv-total-lines">
                                <div><span>Subtotal</span><strong className="inv-mono">{fmt(subtotal)}</strong></div>
                                {discountAmount > 0 && <div className="success"><span>Descuento</span><strong>−{fmt(discountAmount)}</strong></div>}
                                <div><span>ITBIS ({applyItbis ? taxRate : 0}%)</span><strong className="inv-mono">{fmt(tax)}</strong></div>
                                <div className="grand-total"><span>Total</span><strong className="inv-mono">{fmt(total)}</strong></div>
                            </div>
                            <label className="inv-tax-toggle">
                                <input
                                    type="checkbox"
                                    checked={applyItbis}
                                    onChange={(e) => setApplyItbis(e.target.checked)}
                                    disabled={fiscalLocked}
                                />
                                <span>Aplicar ITBIS</span>
                            </label>
                        </div>
                    </section>

                    <section className="inv-card">
                        <div className="inv-card-header">
                            <span><FaMoneyBillWave /> Pago</span>
                        </div>
                        <div className="inv-card-body">
                            <div className="payment-grid">
                                <button type="button" className={`payment-option ${invoice.payment_method === "cash" ? "active-cash" : ""}`} onClick={() => !fiscalLocked && setInvoice({ ...invoice, payment_method: "cash", cash_received: 0 })}>
                                    <FaMoneyBillWave /><span>Efectivo</span>
                                </button>
                                <button type="button" className={`payment-option ${invoice.payment_method === "card" ? "active-card" : ""}`} onClick={() => !fiscalLocked && setInvoice({ ...invoice, payment_method: "card", cash_received: 0 })}>
                                    <FaCreditCard /><span>Tarjeta</span>
                                </button>
                                <button type="button" className={`payment-option ${invoice.payment_method === "transfer" ? "active-transfer" : ""}`} onClick={() => !fiscalLocked && setInvoice({ ...invoice, payment_method: "transfer", cash_received: 0 })}>
                                    <FaExchangeAlt /><span>Transferencia</span>
                                </button>
                            </div>

                            {invoice.payment_method === "cash" && (
                                <div className="inv-payment-cash">
                                    <input
                                        type="number"
                                        step="0.01"
                                        placeholder="Efectivo recibido"
                                        value={invoice.cash_received || ""}
                                        onChange={(e) => setInvoice({ ...invoice, cash_received: parseFloat(e.target.value) || 0 })}
                                        className={errors.cash ? "is-error" : ""}
                                        disabled={fiscalLocked}
                                    />
                                    <div className="inv-quick-cash">
                                        <button type="button" className="inv-btn secondary small" onClick={() => setInvoice({ ...invoice, cash_received: total })} disabled={fiscalLocked}>Exacto</button>
                                        <button type="button" className="inv-btn secondary small" onClick={() => setInvoice({ ...invoice, cash_received: Math.ceil(total / 10) * 10 })} disabled={fiscalLocked}>{fmt(Math.ceil(total / 10) * 10)}</button>
                                        <button type="button" className="inv-btn secondary small" onClick={() => setInvoice({ ...invoice, cash_received: Math.ceil(total / 50) * 50 })} disabled={fiscalLocked}>{fmt(Math.ceil(total / 50) * 50)}</button>
                                    </div>
                                    {errors.cash && <div className="error-text"><FaTimes size={10} /> {errors.cash}</div>}
                                    <div className="change-box">
                                        <span>Cambio</span>
                                        <strong className="inv-mono">{fmt(change)}</strong>
                                    </div>
                                </div>
                            )}
                        </div>
                    </section>

                    <section className="inv-card">
                        <div className="inv-card-body">
                            <div className="inv-save-grid">
                                <button type="button" className="inv-btn secondary" onClick={(e) => submit(e, "new")} disabled={loading || fiscalLocked}>
                                    <FaPlus /> Nuevo
                                </button>
                                <button type="button" className="inv-btn primary" onClick={(e) => submit(e, "save")} disabled={loading || fiscalLocked}>
                                    <FaSave /> {id ? "Actualizar" : "Guardar"}
                                </button>
                            </div>
                        </div>
                    </section>
                </aside>
            </div>

            {/* Modal de productos */}
            {showModal && (
                <div className="inv-modal-backdrop" onClick={(e) => e.target === e.currentTarget && setShowModal(false)}>
                    <div className="inv-product-modal">
                        <div className="inv-card-header">
                            <span><FaSearch /> Productos</span>
                            <button type="button" className="inv-btn secondary icon-only" onClick={() => setShowModal(false)}><FaTimes /></button>
                        </div>
                        <div className="inv-modal-search">
                            <div className="inv-input-icon">
                                <FaSearch />
                                <input
                                    type="text"
                                    placeholder="Buscar por nombre o código..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    autoFocus
                                />
                            </div>
                        </div>
                        <div className="products-grid">
                            {filteredProducts.map(p => (
                                <div key={p.id} className="product-card" onClick={() => { addProduct(p); setShowModal(false); setSearchTerm(""); }}>
                                    <div className="product-card-name">{p.name}</div>
                                    <div className="product-card-code">{p.barcode || "sin código"}</div>
                                    <div className="product-card-meta">
                                        <span>{fmt(p.price)}</span>
                                        <small>Stock: {p.stock}</small>
                                    </div>
                                </div>
                            ))}
                            {filteredProducts.length === 0 && (
                                <div className="inv-modal-empty">No se encontraron productos</div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default InvoiceForm;
