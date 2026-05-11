import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import {
    FaSave, FaPlus, FaTrash, FaArrowLeft, FaPrint, FaCheck,
    FaSearch, FaBarcode, FaEdit, FaRegFilePdf,
    FaMoneyBillWave, FaCreditCard, FaExchangeAlt,
    FaUser, FaBox, FaCalculator, FaTimes, FaTag,
    FaEye, FaEyeSlash
} from "react-icons/fa";
import { toast, Toaster } from "react-hot-toast";
import Swal from "sweetalert2";
import "../css/facturaForm.css";


/* Componente principal */
const InvoiceForm = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [clients, setClients] = useState([]);
    const [products, setProducts] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");
    const [taxRate, setTaxRate] = useState(16);
    const [discount, setDiscount] = useState({ value: 0, type: "percentage" });
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
        const subtotal = invoice.details.reduce((sum, d) => sum + (d.subtotal || d.quantity * d.price), 0);
        let discountAmount = discount.type === "percentage" ? subtotal * (discount.value / 100) : discount.value;
        const afterDiscount = subtotal - discountAmount;
        const tax = afterDiscount * (taxRate / 100);
        const total = afterDiscount + tax;
        const change = invoice.payment_method === "cash" ? Math.max(0, invoice.cash_received - total) : 0;
        return { subtotal, discountAmount: Math.min(discountAmount, subtotal), tax, total, change };
    }, [invoice.details, discount, taxRate, invoice.payment_method, invoice.cash_received]);

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
        setLoading(true);
        const data = {
            client_id: parseInt(invoice.client),
            receipt_type: "invoice",
            payment_method: invoice.payment_method,
            cash_received: parseFloat(invoice.cash_received) || 0,
            discount: discountAmount,
            subtotal,
            tax,
            total,
            change,
            notes: invoice.notes,
            date: invoice.date,
            status: invoice.status,
            details: invoice.details.map(d => ({ product: d.product, quantity: d.quantity, price: d.price }))
        };
        try {
            let res;
            if (id) {
                res = await api.put(`invoices/${id}/`, data);
                toast.success("Factura actualizada");
            } else {
                res = await api.post("invoices/", data);
                toast.success("Factura creada");
            }
            if (action === "new") {
                setInvoice({ client: "", details: [], status: "pending", date: new Date().toISOString().split("T")[0], notes: "", payment_method: "cash", cash_received: 0 });
                setDiscount({ value: 0, type: "percentage" });
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
            title: `¿Marcar como ${status === "paid" ? "pagada" : "cancelada"}?`,
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Confirmar"
        });
        if (result.isConfirmed) {
            try {
                await api.patch(`invoices/${id}/`, { status });
                setInvoice({ ...invoice, status });
                toast.success(`Estado actualizado a ${status === "paid" ? "pagada" : "cancelada"}`);
            } catch {
                toast.error("Error al actualizar");
            }
        }
    };

    const selectedClient = clients.find(c => String(c.id) === String(invoice.client));
    const fmt = (n) => `$${(+n || 0).toFixed(2)}`;

    return (
        <div className="inv-root">
            <Toaster position="top-right" />

            {/* Header */}
            <header className="inv-header">
                <button className="btn btn-outline btn-sm" onClick={() => navigate("/invoice-list")}>
                    <FaArrowLeft size={12} /> Volver
                </button>

                <div className="card-title" style={{ margin: 0 }}>
                    {id ? <><FaEdit /> Editar Factura</> : <><FaRegFilePdf /> Nueva Factura</>}
                    {id && invoice.invoice_number && (
                        <span className="font-mono" style={{ color: "var(--text-muted)" }}>#{invoice.invoice_number}</span>
                    )}
                    {id && (
                        <span className={`status-badge status-${invoice.status === "pending" ? "pending" : invoice.status === "paid" ? "paid" : "cancelled"}`}>
                            {invoice.status === "pending" ? "Pendiente" : invoice.status === "paid" ? "Pagada" : "Cancelada"}
                        </span>
                    )}
                </div>

                <div className="input-wrapper" style={{ flex: 2, minWidth: "200px" }}>
                    <FaBarcode className="input-icon" />
                    <input
                        ref={barcodeRef}
                        type="text"
                        placeholder="    Escanear código de barras..."
                        onKeyPress={(e) => e.key === "Enter" && handleScan(e.target.value)}
                    />
                </div>

                <div className="inv-header-actions">
                    {id && (
                        <button className="btn btn-outline btn-sm" onClick={() => window.open(`/invoice-print/${id}`, "_blank")}>
                            <FaPrint /> Imprimir
                        </button>
                    )}
                    {id && invoice.status === "pending" && (
                        <button className="btn btn-primary btn-sm" onClick={() => changeStatus("paid")}>
                            <FaCheck /> Cobrar
                        </button>
                    )}
                    {id && invoice.status !== "cancelled" && (
                        <button className="btn btn-danger btn-sm" onClick={() => changeStatus("cancelled")}>
                            <FaTimes /> Cancelar
                        </button>
                    )}
                </div>
            </header>

            {/* Grid principal */}
            <div className="inv-grid">
                {/* Columna izquierda - Carrito */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title"><FaBox /> Carrito de compras</span>
                        <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
                            <FaPlus /> Buscar producto
                        </button>
                    </div>

                    {errors.details && (
                        <div style={{ padding: "0.75rem", background: "var(--danger-light)", color: "var(--danger)", fontSize: "0.875rem", margin: "0.75rem 1.25rem", borderRadius: "var(--radius-sm)" }}>
                            ⚠️ {errors.details}
                        </div>
                    )}

                    {invoice.details.length === 0 ? (
                        <div className="cart-empty">
                            <FaBox size={48} style={{ marginBottom: "0.75rem", opacity: 0.3 }} />
                            <p>Escanea un código o busca un producto</p>
                        </div>
                    ) : (
                        <div className="cart-table-container">
                            <table className="cart-table">
                                <thead>
                                    <tr>
                                        <th>Producto</th>
                                        <th style={{ width: 90 }}>Cant.</th>
                                        <th style={{ width: 100 }}>Precio</th>
                                        <th style={{ width: 90, textAlign: "right" }}>Subtotal</th>
                                        <th style={{ width: 40 }}></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {invoice.details.map((item, idx) => (
                                        <tr key={idx}>
                                            <td>
                                                <div style={{ fontWeight: 500 }}>{item.product_name}</div>
                                                {item.barcode && (
                                                    <div style={{ fontSize: "0.6875rem", color: "var(--text-faint)", fontFamily: "monospace" }}>
                                                        <FaBarcode size={9} style={{ marginRight: 4 }} />{item.barcode}
                                                    </div>
                                                )}
                                            </td>
                                            <td>
                                                <input
                                                    type="number"
                                                    className="qty-input"
                                                    min="1"
                                                    value={item.quantity}
                                                    onChange={(e) => updateDetail(idx, "quantity", e.target.value)}
                                                />
                                            </td>
                                            <td>
                                                <input
                                                    type="number"
                                                    className="price-input"
                                                    step="0.01"
                                                    value={item.price}
                                                    onChange={(e) => updateDetail(idx, "price", e.target.value)}
                                                />
                                            </td>
                                            <td className="text-right font-mono" style={{ fontWeight: 600 }}>{fmt(item.subtotal)}</td>
                                            <td>
                                                <button className="btn btn-danger btn-sm" style={{ padding: "0.375rem" }} onClick={() => removeDetail(idx, item.product_name)}>
                                                    <FaTrash size={12} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            <div className="flex-between" style={{ padding: "0.75rem 1rem", borderTop: "1px solid var(--border)", background: "var(--surface-hover)", fontSize: "0.875rem" }}>
                                <span>{invoice.details.reduce((s, d) => s + d.quantity, 0)} unidades</span>
                                <span>Subtotal: <span className="font-mono">{fmt(subtotal)}</span></span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Columna derecha - Panel de gestión */}
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    {/* Cliente */}
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title"><FaUser /> Cliente</span>
                        </div>
                        <div className="card-body">
                            <select
                                className={errors.client ? "is-error" : ""}
                                value={invoice.client}
                                onChange={(e) => setInvoice({ ...invoice, client: e.target.value })}
                                style={{ width: "100%" }}
                            >
                                <option value="">Seleccionar cliente...</option>
                                {clients.map(c => (
                                    <option key={c.id} value={c.id}>{c.name} {c.ruc_ci ? `(${c.ruc_ci})` : ""}</option>
                                ))}
                            </select>
                            {errors.client && <div className="error-text"><FaTimes size={10} /> {errors.client}</div>}
                            {selectedClient && (
                                <div style={{ marginTop: "0.75rem", fontSize: "0.8125rem", background: "var(--primary-light)", padding: "0.5rem 0.75rem", borderRadius: "var(--radius-sm)", color: "var(--primary)" }}>
                                    {selectedClient.email && <span>{selectedClient.email}</span>}
                                    {selectedClient.phone && <span style={{ marginLeft: "0.75rem" }}>📞 {selectedClient.phone}</span>}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Totales y descuentos */}
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title"><FaCalculator /> Totales</span>
                        </div>
                        <div className="card-body space-y-3">
                            <div>
                                <label style={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.25rem", display: "block" }}><FaTag /> Descuento</label>
                                <div style={{ display: "flex", gap: "0.5rem" }}>
                                    <input
                                        type="number"
                                        value={discount.value}
                                        onChange={(e) => setDiscount({ ...discount, value: parseFloat(e.target.value) || 0 })}
                                        style={{ flex: 1 }}
                                    />
                                    <button className={`btn ${discount.type === "percentage" ? "btn-primary" : "btn-outline"}`} onClick={() => setDiscount({ ...discount, type: "percentage" })}>%</button>
                                    <button className={`btn ${discount.type === "fixed" ? "btn-primary" : "btn-outline"}`} onClick={() => setDiscount({ ...discount, type: "fixed" })}>$</button>
                                </div>
                            </div>

                            <div>
                                <label style={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.25rem", display: "block" }}>IVA (%)</label>
                                <input type="number" value={taxRate} onChange={(e) => setTaxRate(parseFloat(e.target.value) || 0)} step="1" />
                            </div>

                            <div className="space-y-2" style={{ marginTop: "0.75rem" }}>
                                <div className="totals-line"><span>Subtotal</span><span className="font-mono">{fmt(subtotal)}</span></div>
                                {discountAmount > 0 && (
                                    <div className="totals-line" style={{ color: "var(--success)" }}><span>Descuento</span><span>−{fmt(discountAmount)}</span></div>
                                )}
                                <div className="totals-line"><span>IVA ({taxRate}%)</span><span className="font-mono">{fmt(tax)}</span></div>
                                <div className="totals-line total"><span>TOTAL</span><span className="font-mono">{fmt(total)}</span></div>
                            </div>
                        </div>
                    </div>

                    {/* Pago */}
                    <div className="card">
                        <div className="card-header">
                            <span className="card-title">Método de pago</span>
                        </div>
                        <div className="card-body">
                            <div className="payment-grid">
                                <div className={`payment-option ${invoice.payment_method === "cash" ? "active-cash" : ""}`} onClick={() => setInvoice({ ...invoice, payment_method: "cash", cash_received: 0 })}>
                                    <FaMoneyBillWave size={20} /><span>Efectivo</span>
                                </div>
                                <div className={`payment-option ${invoice.payment_method === "card" ? "active-card" : ""}`} onClick={() => setInvoice({ ...invoice, payment_method: "card", cash_received: 0 })}>
                                    <FaCreditCard size={20} /><span>Tarjeta</span>
                                </div>
                                <div className={`payment-option ${invoice.payment_method === "transfer" ? "active-transfer" : ""}`} onClick={() => setInvoice({ ...invoice, payment_method: "transfer", cash_received: 0 })}>
                                    <FaExchangeAlt size={20} /><span>Transferencia</span>
                                </div>
                            </div>

                            {invoice.payment_method === "cash" && (
                                <div className="space-y-2">
                                    <input
                                        type="number"
                                        step="0.01"
                                        placeholder="Efectivo recibido"
                                        value={invoice.cash_received || ""}
                                        onChange={(e) => setInvoice({ ...invoice, cash_received: parseFloat(e.target.value) || 0 })}
                                        className={errors.cash ? "is-error" : ""}
                                    />
                                    <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                                        <button className="btn btn-outline btn-sm" onClick={() => setInvoice({ ...invoice, cash_received: total })}>Exacto</button>
                                        <button className="btn btn-outline btn-sm" onClick={() => setInvoice({ ...invoice, cash_received: Math.ceil(total / 10) * 10 })}>{fmt(Math.ceil(total / 10) * 10)}</button>
                                        <button className="btn btn-outline btn-sm" onClick={() => setInvoice({ ...invoice, cash_received: Math.ceil(total / 50) * 50 })}>{fmt(Math.ceil(total / 50) * 50)}</button>
                                    </div>
                                    {errors.cash && <div className="error-text"><FaTimes size={10} /> {errors.cash}</div>}
                                    <div className="change-box">
                                        <span style={{ fontWeight: 600 }}>Cambio</span>
                                        <span className="font-mono" style={{ fontSize: "1.125rem", fontWeight: 700 }}>{fmt(change)}</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Notas y acciones */}
                    <div className="card">
                        <div className="card-body space-y-3">
                            <textarea
                                placeholder="Notas adicionales para el cliente..."
                                rows="3"
                                value={invoice.notes}
                                onChange={(e) => setInvoice({ ...invoice, notes: e.target.value })}
                            />
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                                <button className="btn btn-outline" onClick={(e) => submit(e, "new")} disabled={loading}>
                                    <FaPlus /> Nuevo
                                </button>
                                <button className="btn btn-primary" onClick={(e) => submit(e, "save")} disabled={loading}>
                                    <FaSave /> {id ? "Actualizar" : "Guardar"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Modal de productos */}
            {showModal && (
                <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem" }} onClick={(e) => e.target === e.currentTarget && setShowModal(false)}>
                    <div className="card" style={{ width: "100%", maxWidth: "700px", maxHeight: "80vh", display: "flex", flexDirection: "column" }}>
                        <div className="card-header">
                            <span className="card-title"><FaSearch /> Productos</span>
                            <button className="btn btn-outline btn-sm" onClick={() => setShowModal(false)}><FaTimes /></button>
                        </div>
                        <div style={{ padding: "1rem" }}>
                            <div className="input-wrapper">
                                <FaSearch className="input-icon" />
                                <input
                                    type="text"
                                    placeholder="Buscar por nombre o código..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    autoFocus
                                    style={{ paddingLeft: "2rem" }}
                                />
                            </div>
                        </div>
                        <div className="products-grid" style={{ padding: "0 1rem 1rem 1rem" }}>
                            {products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()) || p.barcode?.includes(searchTerm)).map(p => (
                                <div key={p.id} className="product-card" onClick={() => { addProduct(p); setShowModal(false); setSearchTerm(""); }}>
                                    <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{p.name}</div>
                                    <div style={{ fontSize: "0.6875rem", color: "var(--text-faint)", fontFamily: "monospace" }}>{p.barcode || "sin código"}</div>
                                    <div className="flex-between" style={{ marginTop: "0.5rem" }}>
                                        <span style={{ fontWeight: 700, color: "var(--primary)" }}>{fmt(p.price)}</span>
                                        <span style={{ fontSize: "0.6875rem", background: "var(--surface-hover)", padding: "0.125rem 0.5rem", borderRadius: "999px" }}>Stock: {p.stock}</span>
                                    </div>
                                </div>
                            ))}
                            {products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()) || p.barcode?.includes(searchTerm)).length === 0 && (
                                <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-faint)", gridColumn: "1/-1" }}>No se encontraron productos</div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default InvoiceForm;