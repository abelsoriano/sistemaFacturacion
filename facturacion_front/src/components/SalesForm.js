import React, { useState, useEffect, useRef } from "react";
import api from "../services/api";
import { showGenericAlert, showSuccessAlert, showGenerAlertSioNo } from "../herpert";
import { generatePDF } from './generatePDF';
import placeholderImage from '../assets/placeholder-product.png';
import { useNavigate, useParams } from "react-router-dom";
import { FaArrowLeft} from 'react-icons/fa';
import {
  IconSearch,
  IconPlus,
  IconMinus,
  IconTrash,
  IconCart,
  IconUser,
  IconUserPlus,
  IconCheck,
  IconX,
} from './Icons';

// ─── Estilos ───────────────────────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

  :root {
    --bg: #f5f4f0;
    --surface: #ffffff;
    --surface-2: #f9f8f5;
    --border: #e8e5de;
    --border-strong: #d4cfc4;
    --text-primary: #1a1814;
    --text-secondary: #6b6560;
    --text-muted: #9d9890;
    --accent: #2d6a4f;
    --accent-hover: #245a42;
    --accent-light: #d8f0e5;
    --accent-text: #1a4a33;
    --danger: #c0392b;
    --danger-light: #fdecea;
    --warning: #e67e22;
    --warning-light: #fef5ec;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg: 0 12px 32px rgba(0,0,0,0.10);
    --radius: 10px;
    --radius-sm: 6px;
    --radius-lg: 16px;
    --font: 'DM Sans', sans-serif;
    --font-mono: 'DM Mono', monospace;
    --transition: 0.18s cubic-bezier(0.4,0,0.2,1);
  }

  .sale-root { font-family: var(--font); background: var(--bg); min-height: 100vh; padding: 24px; }

  /* ── Header ── */
  .sale-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
  .sale-title { font-size: 20px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.4px; }
  .sale-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

  /* ── Layout 3 columnas ── */
  .sale-layout {
    display: grid;
    grid-template-columns: 280px 1fr 360px;
    gap: 16px;
    align-items: start;
  }

  /* ── Panel base ── */
  .panel {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-sm);
  }
  .panel-header {
    padding: 14px 18px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
  }
  .panel-title { font-size: 14px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 7px; }
  .panel-body { padding: 14px 18px; }

  /* ── Pestañas cliente ── */
  .client-tabs { display: flex; border-bottom: 1px solid var(--border); }
  .client-tab {
    flex: 1; padding: 10px 8px; font-size: 12px; font-weight: 500;
    cursor: pointer; border: none; background: transparent;
    font-family: var(--font); color: var(--text-secondary);
    border-bottom: 2px solid transparent; transition: all var(--transition);
  }
  .client-tab.active {
    color: var(--accent); border-bottom-color: var(--accent);
    background: var(--accent-light);
  }
  .client-tab-body { padding: 14px 18px; }

  /* ── Búsqueda cliente ── */
  .search-input-wrap { position: relative; }
  .search-input-wrap input {
    width: 100%; padding: 9px 12px 9px 34px; border: 1.5px solid var(--border);
    border-radius: var(--radius-sm); font-size: 13px; background: var(--surface-2);
    color: var(--text-primary); outline: none; transition: border-color var(--transition);
    font-family: var(--font); box-sizing: border-box;
  }
  .search-input-wrap input:focus { border-color: var(--accent); background: var(--surface); }
  .search-input-wrap .icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; }

  .client-dropdown {
    position: absolute; top: calc(100% + 5px); left: 0; right: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-sm); box-shadow: var(--shadow-lg);
    z-index: 100; max-height: 200px; overflow-y: auto;
  }
  .client-option {
    padding: 9px 12px; cursor: pointer; font-size: 13px; color: var(--text-primary);
    transition: background var(--transition); display: flex; align-items: center; gap: 9px;
  }
  .client-option:hover { background: var(--surface-2); }
  .client-option-name { font-weight: 500; font-size: 13px; }
  .client-option-meta { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

  /* ── Estado del cliente seleccionado ── */
  .client-status-box {
    margin-top: 10px; padding: 9px 12px; border-radius: var(--radius-sm);
    font-size: 12px; font-weight: 500;
  }
  .client-status-box.empty {
    background: var(--surface-2); color: var(--text-muted);
    border: 1px dashed var(--border-strong);
    display: flex; align-items: center; gap: 7px;
  }
  .client-status-box.selected {
    background: var(--accent-light); color: var(--accent-text);
    border: 1px solid #b2dfca;
    display: flex; align-items: center; gap: 7px;
  }
  .client-status-box.selected .client-clear {
    margin-left: auto; cursor: pointer; color: var(--accent);
    display: flex; align-items: center;
  }

  .divider-text {
    font-size: 11px; color: var(--text-muted); margin: 12px 0;
    display: flex; align-items: center; gap: 8px;
  }
  .divider-text::before, .divider-text::after { content: ''; flex: 1; height: 1px; background: var(--border); }

  .btn-new-client {
    width: 100%; padding: 9px; background: transparent; color: var(--accent);
    border: 1.5px dashed var(--accent); border-radius: var(--radius-sm);
    font-size: 13px; font-weight: 500; cursor: pointer;
    transition: all var(--transition); font-family: var(--font);
    display: flex; align-items: center; justify-content: center; gap: 7px;
  }
  .btn-new-client:hover { background: var(--accent-light); }

  /* ── Badge cliente activo (en panel de productos) ── */
  .active-client-badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: var(--accent-light); color: var(--accent-text);
    padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;
  }

  /* ── Búsqueda de productos ── */
  .product-search-input {
    width: 100%; padding: 9px 12px 9px 36px;
    border: 1.5px solid var(--border); border-radius: var(--radius-sm);
    font-size: 13px; background: var(--surface-2); color: var(--text-primary);
    outline: none; transition: all var(--transition); font-family: var(--font);
    box-sizing: border-box; margin-bottom: 12px;
  }
  .product-search-input:focus { border-color: var(--accent); background: var(--surface); }

  .product-list { display: flex; flex-direction: column; gap: 7px; max-height: 520px; overflow-y: auto; }
  .product-list::-webkit-scrollbar { width: 4px; }
  .product-list::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 4px; }

  .product-card {
    display: flex; align-items: center; gap: 12px;
    padding: 10px; border: 1px solid var(--border); border-radius: var(--radius);
    transition: all var(--transition); background: var(--surface);
  }
  .product-card:hover { border-color: var(--accent); }
  .product-card.out-of-stock { opacity: 0.5; }

  .product-thumb {
    width: 50px; height: 50px; border-radius: var(--radius-sm);
    overflow: hidden; flex-shrink: 0; border: 1px solid var(--border);
    cursor: pointer; background: var(--surface-2);
  }
  .product-thumb img { width: 100%; height: 100%; object-fit: cover; }

  .product-info { flex: 1; min-width: 0; }
  .product-name { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .product-desc { font-size: 11px; color: var(--text-muted); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .product-meta { display: flex; align-items: center; gap: 10px; margin-top: 5px; }
  .product-price { font-size: 14px; font-weight: 700; color: var(--accent); font-family: var(--font-mono); }
  .product-stock { font-size: 10px; padding: 2px 7px; border-radius: 10px; font-weight: 600; }
  .stock-ok { background: var(--accent-light); color: var(--accent-text); }
  .stock-low { background: var(--warning-light); color: var(--warning); }
  .stock-out { background: var(--danger-light); color: var(--danger); }

  .btn-add {
    padding: 7px 14px; background: var(--accent); color: white;
    border: none; border-radius: var(--radius-sm); font-size: 12px; font-weight: 600;
    cursor: pointer; transition: background var(--transition); white-space: nowrap;
    font-family: var(--font); flex-shrink: 0; display: flex; align-items: center; gap: 5px;
  }
  .btn-add:hover { background: var(--accent-hover); }
  .btn-add:disabled { background: var(--border-strong); color: var(--text-muted); cursor: not-allowed; }

  .empty-state { text-align: center; padding: 36px 16px; color: var(--text-muted); }
  .empty-state svg { opacity: 0.25; margin-bottom: 10px; }
  .empty-state p { font-size: 13px; }

  .spinner-wrap { display: flex; justify-content: center; padding: 36px; }
  .spinner {
    width: 24px; height: 24px; border: 2px solid var(--border);
    border-top-color: var(--accent); border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Carrito ── */
  .cart-panel { position: sticky; top: 20px; }

  .cart-items-body { padding: 0 18px; }
  .cart-item {
    display: flex; align-items: center; gap: 8px;
    padding: 9px 0; border-bottom: 1px solid var(--border);
  }
  .cart-item:last-child { border-bottom: none; }

  .cart-item-thumb {
    width: 38px; height: 38px; border-radius: var(--radius-sm);
    overflow: hidden; flex-shrink: 0; border: 1px solid var(--border);
    background: var(--surface-2); cursor: pointer;
  }
  .cart-item-thumb img { width: 100%; height: 100%; object-fit: cover; }

  .cart-item-info { flex: 1; min-width: 0; }
  .cart-item-name { font-size: 12px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .cart-item-price { font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px; }

  .cart-item-controls { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
  .qty-btn {
    width: 22px; height: 22px; border: 1.5px solid var(--border); background: var(--surface);
    border-radius: 5px; cursor: pointer; display: flex; align-items: center; justify-content: center;
    color: var(--text-secondary); transition: all var(--transition);
  }
  .qty-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
  .qty-value { font-size: 12px; font-weight: 600; color: var(--text-primary); min-width: 18px; text-align: center; font-family: var(--font-mono); }

  .cart-item-subtotal { font-size: 12px; font-weight: 700; color: var(--accent); font-family: var(--font-mono); min-width: 54px; text-align: right; }

  .btn-remove {
    width: 22px; height: 22px; border: 1.5px solid var(--border); background: transparent;
    border-radius: 5px; cursor: pointer; display: flex; align-items: center; justify-content: center;
    color: var(--text-muted); transition: all var(--transition); flex-shrink: 0;
  }
  .btn-remove:hover { border-color: var(--danger); color: var(--danger); background: var(--danger-light); }

  .cart-empty-state { text-align: center; padding: 30px 16px; color: var(--text-muted); }
  .cart-empty-state svg { opacity: 0.2; margin-bottom: 8px; }
  .cart-empty-state p { font-size: 12px; }

  .cart-footer { padding: 14px 18px; border-top: 2px solid var(--border); }
  .cart-total-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .cart-total-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; }
  .cart-total-value { font-size: 22px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
  .cart-items-count { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

  .btn-checkout {
    width: 100%; padding: 12px; background: var(--accent); color: white;
    border: none; border-radius: var(--radius-sm); font-size: 14px; font-weight: 600;
    cursor: pointer; transition: background var(--transition); font-family: var(--font);
    display: flex; align-items: center; justify-content: center; gap: 7px;
  }
  .btn-checkout:hover { background: var(--accent-hover); }

  .btn-cancel-sale {
    width: 100%; padding: 8px; margin-top: 7px; background: transparent;
    color: var(--text-muted); border: 1px solid var(--border);
    border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;
    transition: all var(--transition); font-family: var(--font);
  }
  .btn-cancel-sale:hover { border-color: var(--danger); color: var(--danger); background: var(--danger-light); }

  /* ── Shake + highlight cliente ── */
  @keyframes shake {
    0%,100% { transform: translateX(0); }
    15%      { transform: translateX(-6px); }
    30%      { transform: translateX(6px); }
    45%      { transform: translateX(-5px); }
    60%      { transform: translateX(5px); }
    75%      { transform: translateX(-3px); }
    90%      { transform: translateX(3px); }
  }
  .shake-anim { animation: shake 0.45s ease; }
  .client-col-highlight { box-shadow: 0 0 0 2.5px var(--warning), var(--shadow-md) !important; transition: box-shadow 0.2s; }
  .client-required-msg {
    margin: 8px 18px 10px; padding: 8px 12px;
    background: var(--warning-light); border: 1px solid #f0c27a;
    border-radius: var(--radius-sm); font-size: 12px; color: var(--warning);
    font-weight: 600; display: flex; align-items: center; gap: 7px;
  }

  /* ── Clear button en inputs ── */
  .input-with-clear { position: relative; }
  .input-clear-btn {
    position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
    width: 18px; height: 18px; border: none; background: var(--border-strong);
    border-radius: 50%; cursor: pointer; display: flex; align-items: center;
    justify-content: center; color: var(--text-secondary); padding: 0;
    transition: all var(--transition); flex-shrink: 0;
  }
  .input-clear-btn:hover { background: var(--danger); color: white; }

  /* ── Modal de pago ── */
  .pay-modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.45);
    display: flex; align-items: center; justify-content: center; z-index: 1000;
    backdrop-filter: blur(3px); animation: fadeIn 0.2s;
  }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  .pay-modal {
    background: var(--surface); border-radius: var(--radius-lg);
    width: 420px; max-width: 95vw; box-shadow: var(--shadow-lg);
    animation: slideUp 0.22s cubic-bezier(0.34,1.56,0.64,1);
  }
  @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

  .pay-modal-header {
    padding: 18px 22px 14px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
  }
  .pay-modal-title { font-size: 16px; font-weight: 700; color: var(--text-primary); }
  .pay-modal-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
  .modal-close {
    width: 30px; height: 30px; border: 1px solid var(--border); background: transparent;
    border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center;
    color: var(--text-muted); transition: all var(--transition);
  }
  .modal-close:hover { border-color: var(--danger); color: var(--danger); }

  .pay-modal-body { padding: 18px 22px; }
  .pay-modal-footer { padding: 14px 22px 18px; border-top: 1px solid var(--border); display: flex; gap: 10px; }

  .form-group { margin-bottom: 14px; }
  .form-label { font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 5px; }
  .form-control {
    width: 100%; padding: 9px 12px; border: 1.5px solid var(--border);
    border-radius: var(--radius-sm); font-size: 13px; color: var(--text-primary);
    background: var(--surface); outline: none; transition: border-color var(--transition);
    font-family: var(--font); box-sizing: border-box;
  }
  .form-control:focus { border-color: var(--accent); }
  .form-control:read-only { background: var(--surface-2); color: var(--text-secondary); }
  select.form-control { cursor: pointer; }

  .total-display {
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 12px 14px; margin-bottom: 14px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .total-display-label { font-size: 12px; color: var(--text-secondary); }
  .total-display-value { font-size: 22px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }

  .change-display {
    background: var(--accent-light); border: 1px solid #b2dfca;
    border-radius: var(--radius-sm); padding: 9px 12px;
    display: flex; justify-content: space-between; align-items: center; margin-top: 10px;
  }
  .change-label { font-size: 12px; color: var(--accent-text); font-weight: 500; }
  .change-value { font-size: 16px; font-weight: 700; color: var(--accent); font-family: var(--font-mono); }
  .change-insufficient { background: var(--danger-light); border-color: #f5c6c2; }
  .change-insufficient .change-label, .change-insufficient .change-value { color: var(--danger); }

  .payment-methods { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; margin-bottom: 4px; }
  .payment-method-btn {
    padding: 9px 8px; border: 1.5px solid var(--border); background: var(--surface);
    border-radius: var(--radius-sm); font-size: 12px; font-weight: 500;
    cursor: pointer; text-align: center; transition: all var(--transition);
    font-family: var(--font); color: var(--text-secondary);
  }
  .payment-method-btn.selected { border-color: var(--accent); background: var(--accent-light); color: var(--accent-text); font-weight: 600; }

  .btn-primary-pay {
    flex: 1; padding: 11px; background: var(--accent); color: white;
    border: none; border-radius: var(--radius-sm); font-size: 14px; font-weight: 600;
    cursor: pointer; transition: background var(--transition); font-family: var(--font);
    display: flex; align-items: center; justify-content: center; gap: 7px;
  }
  .btn-primary-pay:hover { background: var(--accent-hover); }
  .btn-primary-pay:disabled { opacity: 0.45; cursor: not-allowed; }
  .btn-secondary-pay {
    padding: 11px 18px; background: transparent; color: var(--text-secondary);
    border: 1.5px solid var(--border); border-radius: var(--radius-sm);
    font-size: 13px; font-weight: 500; cursor: pointer;
    transition: all var(--transition); font-family: var(--font);
  }
  .btn-secondary-pay:hover { border-color: var(--border-strong); color: var(--text-primary); }

  /* ── Modal imagen ── */
  .img-modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.75);
    display: flex; align-items: center; justify-content: center; z-index: 1100;
    cursor: pointer; animation: fadeIn 0.15s;
  }
  .img-modal-content { max-width: 90vw; max-height: 85vh; border-radius: var(--radius); overflow: hidden; }
  .img-modal-content img { max-width: 90vw; max-height: 85vh; display: block; }

  /* ── Responsive ── */
  @media (max-width: 1024px) {
    .sale-layout { grid-template-columns: 260px 1fr 320px; }
  }
  @media (max-width: 860px) {
    .sale-layout { grid-template-columns: 1fr 1fr; }
    .client-col { grid-column: 1 / -1; }
  }
  @media (max-width: 600px) {
    .sale-layout { grid-template-columns: 1fr; }
  }
`;

// ─── Componente principal ──────────────────────────────────────────────────────
const Sale = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const editing = !!id;

  // ── Cliente ──
  const [clientMode, setClientMode] = useState("existing");
  const [clientSearch, setClientSearch] = useState("");
  const [clients, setClients] = useState([]);
  const [filteredClients, setFilteredClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [showClientDropdown, setShowClientDropdown] = useState(false);
  const [quickName, setQuickName] = useState("");
  const clientDropdownRef = useRef(null);

  // ── Productos ──
  const [searchTerm, setSearchTerm] = useState("");
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  // ── Carrito ──
  const [cart, setCart] = useState([]);

  // ── Pago ──
  const [receiptType, setReceiptType] = useState("ticket");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [cashReceived, setCashReceived] = useState("");
  const [change, setChange] = useState(0);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [processingPayment, setProcessingPayment] = useState(false);

  // ── Modal imagen ──
  const [showImageModal, setShowImageModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState("");

  // ── UI feedback cliente ──
  const [clientHighlight, setClientHighlight] = useState(false);
  const clientColRef = useRef(null);

  // ── Cargar clientes ──
  useEffect(() => {
    api.get("/clients/").then(r => setClients(r.data)).catch(() => {});
  }, []);

  // ── Cargar venta para edición si viene el id en la ruta ──
  useEffect(() => {
    if (!editing) return;
    const fetchSale = async () => {
      try {
        const res = await api.get(`/salesUpdate/${id}/`);
        const data = res.data;
        // Poblado básico: cliente
        if (data.client_id) {
          setSelectedClient({ id: data.client_id, name: data.client_name || data.customer });
          setClientSearch(data.client_name || data.customer || '');
          setClientMode('existing');
        } else {
          setQuickName(data.customer || '');
          setClientMode('quick');
        }
        // Recibir detalles al carrito
        if (Array.isArray(data.details)) {
          const mapped = data.details.map(d => ({
            id: d.product || d.product_id || d.product,
            name: d.product_name || d.description || 'N/A',
            price: parseFloat(d.price || d.unit_price || 0),
            quantity: d.quantity || 1,
            stock: d.stock || 999,
            image_url: placeholderImage,
          }));
          setCart(mapped);
        }
        // Otros campos
        if (data.receipt_type) setReceiptType(data.receipt_type);
        if (data.payment_method) setPaymentMethod(data.payment_method);
        if (data.cash_received) setCashReceived(String(data.cash_received));
      } catch (err) {
        console.error('No se pudo cargar la venta:', err);
        showGenericAlert('No se pudo cargar la venta para edición');
      }
    };
    fetchSale();
  }, [editing, id]);

  // ── Filtrar clientes ──
  useEffect(() => {
    if (!clientSearch.trim()) { setFilteredClients(clients.slice(0, 8)); return; }
    const lower = clientSearch.toLowerCase();
    setFilteredClients(
      clients.filter(c =>
        c.name.toLowerCase().includes(lower) ||
        (c.ruc_ci && c.ruc_ci.toLowerCase().includes(lower)) ||
        (c.phone && c.phone.includes(lower))
      ).slice(0, 8)
    );
  }, [clientSearch, clients]);

  // ── Calcular cambio ──
  const cartTotal = cart.reduce((s, i) => s + i.price * i.quantity, 0);
  useEffect(() => {
    setChange((parseFloat(cashReceived) || 0) - cartTotal);
  }, [cashReceived, cartTotal]);

  // ── Cerrar dropdown al click afuera ──
  useEffect(() => {
    const handler = (e) => {
      if (clientDropdownRef.current && !clientDropdownRef.current.contains(e.target)) {
        setShowClientDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ── Nombre activo de display ──
  const getActiveDisplayName = () => {
    if (clientMode === "existing" && selectedClient) return selectedClient.name;
    if (clientMode === "quick" && quickName.trim()) return quickName.trim();
    return null;
  };
  const displayName = getActiveDisplayName();

  // ── Buscar productos ──
  const handleSearch = async (term) => {
    setSearchTerm(term);
    if (!term.trim()) { setProducts([]); return; }
    setLoading(true);
    try {
      const response = await api.get(`/products/?search=${term}`);
      setProducts(response.data.map(p => ({ ...p, image_url: p.image_url || placeholderImage })));
    } catch {
      showGenericAlert("Error al buscar productos");
    } finally {
      setLoading(false);
    }
  };

  // ── Carrito ──
  const addToCart = (product) => {
    const existing = cart.find(i => i.id === product.id);
    if (existing) {
      if (existing.quantity + 1 > product.stock) {
        showGenericAlert(`Stock insuficiente para ${product.name}`);
        return;
      }
      setCart(cart.map(i => i.id === product.id ? { ...i, quantity: i.quantity + 1 } : i));
    } else {
      if (product.stock < 1) { showGenericAlert(`${product.name} está agotado`); return; }
      setCart([...cart, { ...product, quantity: 1 }]);
    }
  };

  const updateQuantity = (productId, qty) => {
    if (qty < 1) { removeFromCart(productId); return; }
    const item = cart.find(i => i.id === productId);
    if (!item) return;
    if (qty > item.stock) { showGenericAlert(`Stock insuficiente para ${item.name}`); return; }
    setCart(cart.map(i => i.id === productId ? { ...i, quantity: qty } : i));
  };

  const removeFromCart = (productId) => setCart(cart.filter(i => i.id !== productId));

  const clearCart = () => {
    setCart([]);
    setSelectedClient(null);
    setClientSearch("");
    setQuickName("");
  };

  // ── Shake el panel de cliente ──
  const triggerClientShake = () => {
    setClientHighlight(true);
    if (clientColRef.current) {
      clientColRef.current.classList.remove("shake-anim");
      void clientColRef.current.offsetWidth;
      clientColRef.current.classList.add("shake-anim");
      setTimeout(() => {
        if (clientColRef.current) clientColRef.current.classList.remove("shake-anim");
      }, 500);
    }
    setTimeout(() => setClientHighlight(false), 2000);
  };

  const handleCheckout = () => {
    if (!displayName) {
      triggerClientShake();
      return;
    }
    setShowPaymentModal(true);
  };

  // ── Confirmar venta ──
  const confirmInvoice = async () => {
    if (cart.length === 0) { showGenericAlert("El carrito está vacío"); return; }
    if (!displayName) { triggerClientShake(); return; }
    if (paymentMethod === "cash" && parseFloat(cashReceived || 0) < cartTotal) {
      showGenericAlert("El efectivo recibido es insuficiente");
      return;
    }

    const subtotal = parseFloat(cartTotal.toFixed(2));
    const tax = parseFloat((subtotal * 0.18).toFixed(2));
    const discount = 0;
    const finalTotal = parseFloat((subtotal + tax - discount).toFixed(2));
    const cash = paymentMethod === "cash" ? parseFloat(parseFloat(cashReceived).toFixed(2)) : finalTotal;
    const changeAmount = parseFloat(Math.max(0, cash - finalTotal).toFixed(2));
    const clientId = clientMode === "existing" && selectedClient ? selectedClient.id : null;

    const invoiceData = {
      ...(clientId ? { client_id: clientId } : {}),
      receipt_type: receiptType,
      payment_method: paymentMethod,
      cash_received: cash,
      discount,
      subtotal,
      tax,
      total: finalTotal,
      change: changeAmount,
      notes: clientId ? "" : `Venta rápida: ${displayName}`,
      date: new Date().toISOString().slice(0, 10),
      status: "paid",
      details: cart.map(item => ({
        product: item.id,
        quantity: item.quantity,
        price: parseFloat(parseFloat(item.price).toFixed(2)),
        product_name: item.name,
        description: item.description || item.name,
      })),
    };

    setProcessingPayment(true);
    try {
      if (editing) {
        // Actualizar la venta existente
        const salePayload = {
          customer: displayName,
          details: cart.map(item => ({
            product: item.id,
            quantity: item.quantity,
            price: parseFloat(parseFloat(item.price).toFixed(2)),
            product_name: item.name,
          })),
        };
        await api.put(`/salesUpdate/${id}/`, salePayload);
        showSuccessAlert("Venta actualizada correctamente");
        setShowPaymentModal(false);
        navigate('/salesList');
      } else {
        const invoiceResponse = await api.post("/invoices/", invoiceData);
        await api.post("/sales/", {
          customer: displayName,
          details: cart.map(item => ({
            product: item.id,
            quantity: item.quantity,
            price: parseFloat(parseFloat(item.price).toFixed(2)),
            product_name: item.name,
          })),
        });

        setCart([]);
        setCashReceived("");
        setChange(0);
        setShowPaymentModal(false);
        showSuccessAlert("Venta registrada exitosamente");

        const shouldPrint = await showGenerAlertSioNo("¿Deseas imprimir la factura?");
        if (shouldPrint) {
          generatePDF(
            { ...invoiceData, invoice_number: invoiceResponse.data.invoice_number },
            {
              filename: `venta_${invoiceResponse.data.invoice_number || invoiceResponse.data.id || 'ticket'}.pdf`,
              showClientName: true,
              showNotes: true,
            }
          );
        }

        const continueWith = await showGenerAlertSioNo(`¿Hacer otra venta para ${displayName}?`);
        if (!continueWith) {
          setSelectedClient(null);
          setClientSearch("");
          setQuickName("");
        }
      }
    } catch (error) {
      console.error("Error en venta:", error.response?.data || error.message);
      const errorMessage = error.response?.data?.error || error.response?.data?.details?.[0]?.detail || error.message || "No se pudo completar la venta. Verifique los datos.";
      showGenericAlert(errorMessage);
    } finally {
      setProcessingPayment(false);
    }
  };

  const insufficientCash = paymentMethod === "cash" && parseFloat(cashReceived || 0) < cartTotal;
  const cartCount = cart.reduce((s, i) => s + i.quantity, 0);

  return (
    <>
      <style>{css}</style>
      <div className="sale-root">
        <button className="cl-btn cl-btn-outline cl-btn-sm" onClick={() => navigate('/salesList')}>
          <FaArrowLeft size={12} /> Volver
        </button>
        {/* ── Header ── */}
        <div className="sale-header">
          
          <div>
            <div className="sale-title">Punto de Venta</div>
            <div className="sale-subtitle">
              {displayName ? `Cliente activo: ${displayName}` : "Seleccione un cliente para registrar la venta"}
            </div>
          </div>
        </div>

        {/* ── Layout 3 columnas ── */}
        <div className="sale-layout">

          {/* ────────────────── COLUMNA 1: Cliente ────────────────── */}
          <div
            ref={clientColRef}
            className={`panel client-col${clientHighlight ? " client-col-highlight" : ""}`}
          >
            {clientHighlight && (
              <div className="client-required-msg">
                ⚠ Seleccione o ingrese un cliente para continuar
              </div>
            )}
            <div className="client-tabs">
              <button
                className={`client-tab ${clientMode === "existing" ? "active" : ""}`}
                onClick={() => setClientMode("existing")}
              >
                Cliente registrado
              </button>
              <button
                className={`client-tab ${clientMode === "quick" ? "active" : ""}`}
                onClick={() => setClientMode("quick")}
              >
                Venta rápida
              </button>
            </div>

            {/* ── Pestaña: cliente existente ── */}
            {clientMode === "existing" && (
              <div className="client-tab-body">
                <label>Buscar cliente</label>
                <div style={{ position: "relative" }} ref={clientDropdownRef}>
                  <div className="search-input-wrap input-with-clear">
                    <span className="icon"><IconSearch /></span>
                    <input
                      type="text"
                      placeholder="Nombre, RUC/CI o teléfono..."
                      value={selectedClient ? selectedClient.name : clientSearch}
                      onChange={(e) => {
                        setClientSearch(e.target.value);
                        setSelectedClient(null);
                        setShowClientDropdown(true);
                      }}
                      onFocus={() => setShowClientDropdown(true)}
                      style={{ paddingRight: (selectedClient || clientSearch) ? 32 : 14 }}
                    />
                    {(selectedClient || clientSearch) && (
                      <button
                        className="input-clear-btn"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          setSelectedClient(null);
                          setClientSearch("");
                          setShowClientDropdown(false);
                        }}
                        title="Limpiar"
                      >
                        <IconX />
                      </button>
                    )}
                  </div>
                  {showClientDropdown && filteredClients.length > 0 && (
                    <div className="client-dropdown">
                      {filteredClients.map(c => (
                        <div
                          key={c.id}
                          className="client-option"
                          onMouseDown={() => {
                            setSelectedClient(c);
                            setClientSearch(c.name);
                            setShowClientDropdown(false);
                          }}
                        >
                          <IconUser />
                          <div>
                            <div className="client-option-name">{c.name}</div>
                            {(c.ruc_ci || c.phone) && (
                              <div className="client-option-meta">
                                {c.ruc_ci}{c.ruc_ci && c.phone ? " · " : ""}{c.phone}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Estado selección */}
                {selectedClient ? (
                  <div className="client-status-box selected">
                    <IconCheck />
                    <span style={{ fontWeight: 600 }}>{selectedClient.name}</span>
                    {selectedClient.client_type && (
                      <span style={{ color: "var(--accent)", fontSize: 11, marginLeft: "auto", fontWeight: 400 }}>
                        {selectedClient.client_type}
                      </span>
                    )}
                    <span
                      className="client-clear"
                      onClick={() => { setSelectedClient(null); setClientSearch(""); }}
                    >
                      <IconX />
                    </span>
                  </div>
                ) : (
                  <div className="client-status-box empty">
                    <IconUser /> Ningún cliente seleccionado
                  </div>
                )}

                <div className="divider-text">o</div>
                <button className="btn-new-client" onClick={() => navigate("/clients/new")}>
                  <IconUserPlus /> Registrar nuevo cliente
                </button>
              </div>
            )}

            {/* ── Pestaña: venta rápida ── */}
            {clientMode === "quick" && (
              <div className="client-tab-body">
                <label>Nombre del cliente</label>
                <div className="search-input-wrap">
                  <span className="icon"><IconUser /></span>
                  <input
                    type="text"
                    placeholder="Ej: Consumidor Final"
                    value={quickName}
                    onChange={(e) => setQuickName(e.target.value)}
                  />
                </div>
                {quickName.trim() ? (
                  <div className="client-status-box selected" style={{ marginTop: 10 }}>
                    <IconCheck />
                    <span style={{ fontWeight: 600 }}>{quickName.trim()}</span>
                  </div>
                ) : (
                  <div className="client-status-box empty" style={{ marginTop: 10 }}>
                    <IconUser /> Ingrese un nombre
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ────────────────── COLUMNA 2: Productos ────────────────── */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <IconSearch /> Productos
              </div>
              {displayName && (
                <div className="active-client-badge">
                  <IconUser /> {displayName}
                </div>
              )}
            </div>
            <div className="panel-body">
              <div className="input-with-clear" style={{ position: "relative" }}>
                <span style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", pointerEvents: "none" }}>
                  <IconSearch />
                </span>
                <input
                  type="text"
                  className="product-search-input"
                  placeholder="Buscar por nombre, código o descripción..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  style={{ paddingRight: searchTerm ? 32 : 12 }}
                />
                {searchTerm && (
                  <button
                    className="input-clear-btn"
                    onClick={() => { setSearchTerm(""); setProducts([]); }}
                    title="Limpiar búsqueda"
                  >
                    <IconX />
                  </button>
                )}
              </div>

              {loading ? (
                <div className="spinner-wrap"><div className="spinner" /></div>
              ) : products.length > 0 ? (
                <div className="product-list">
                  {products.map(product => {
                    const stockClass = product.stock === 0 ? "stock-out" : product.stock <= 3 ? "stock-low" : "stock-ok";
                    const stockLabel = product.stock === 0 ? "Agotado" : `Stock: ${product.stock}`;
                    return (
                      <div key={product.id} className={`product-card ${product.stock < 1 ? "out-of-stock" : ""}`}>
                        <div
                          className="product-thumb"
                          onClick={() => {
                            if (product.image_url !== placeholderImage) {
                              setSelectedImage(product.image_url);
                              setShowImageModal(true);
                            }
                          }}
                        >
                          <img
                            src={product.image_url}
                            alt={product.name}
                            onError={(e) => { e.target.onerror = null; e.target.src = placeholderImage; }}
                          />
                        </div>
                        <div className="product-info">
                          <div className="product-name">{product.name}</div>
                          <div className="product-desc">{product.description || "Sin descripción"}</div>
                          <div className="product-meta">
                            <span className="product-price">${parseFloat(product.price).toFixed(2)}</span>
                            <span className={`product-stock ${stockClass}`}>{stockLabel}</span>
                          </div>
                        </div>
                        <button
                          className="btn-add"
                          onClick={() => addToCart(product)}
                          disabled={product.stock < 1}
                        >
                          {product.stock < 1 ? "Agotado" : <><IconPlus /> Agregar</>}
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="empty-state">
                  <div style={{ display: "flex", justifyContent: "center" }}><IconSearch /></div>
                  <p>{searchTerm ? "No se encontraron productos" : "Ingrese un término de búsqueda"}</p>
                </div>
              )}
            </div>
          </div>

          {/* ────────────────── COLUMNA 3: Carrito ────────────────── */}
          <div className="panel cart-panel">
            <div className="panel-header">
              <div className="panel-title">
                <IconCart /> Carrito
              </div>
              {cart.length > 0 && (
                <span style={{ fontSize: 11, background: "var(--accent)", color: "white", borderRadius: 12, padding: "2px 8px", fontWeight: 600 }}>
                  {cart.length}
                </span>
              )}
            </div>

            <div className="cart-items-body">
              {cart.length === 0 ? (
                <div className="cart-empty-state">
                  <div style={{ display: "flex", justifyContent: "center" }}><IconCart /></div>
                  <p style={{ marginTop: 6 }}>El carrito está vacío</p>
                </div>
              ) : (
                cart.map(item => (
                  <div key={item.id} className="cart-item">
                    <div
                      className="cart-item-thumb"
                      onClick={() => {
                        if (item.image_url && item.image_url !== placeholderImage) {
                          setSelectedImage(item.image_url);
                          setShowImageModal(true);
                        }
                      }}
                    >
                      <img
                        src={item.image_url || placeholderImage}
                        alt={item.name}
                        onError={(e) => { e.target.onerror = null; e.target.src = placeholderImage; }}
                      />
                    </div>
                    <div className="cart-item-info">
                      <div className="cart-item-name">{item.name}</div>
                      <div className="cart-item-price">${parseFloat(item.price).toFixed(2)} c/u</div>
                    </div>
                    <div className="cart-item-controls">
                      <button className="qty-btn" onClick={() => updateQuantity(item.id, item.quantity - 1)}><IconMinus /></button>
                      <span className="qty-value">{item.quantity}</span>
                      <button className="qty-btn" onClick={() => updateQuantity(item.id, item.quantity + 1)}><IconPlus /></button>
                    </div>
                    <div className="cart-item-subtotal">${(item.price * item.quantity).toFixed(2)}</div>
                    <button className="btn-remove" onClick={() => removeFromCart(item.id)}><IconX /></button>
                  </div>
                ))
              )}
            </div>

            {cart.length > 0 && (
              <div className="cart-footer">
                <div className="cart-total-row">
                  <div>
                    <div className="cart-total-label">Total</div>
                    <div className="cart-items-count">{cartCount} artículo{cartCount !== 1 ? "s" : ""}</div>
                  </div>
                  <div className="cart-total-value">${cartTotal.toFixed(2)}</div>
                </div>
                <button
                  className="btn-checkout"
                  onClick={handleCheckout}
                >
                  <IconCheck /> Cobrar
                </button>
                <button className="btn-cancel-sale" onClick={clearCart}>
                  Vaciar carrito
                </button>
              </div>
            )}
          </div>

        </div>

          

      


        {/* ── Modal imagen ampliada ── */}
        {showImageModal && (
          <div className="img-modal-overlay" onClick={() => setShowImageModal(false)}>
            <div className="img-modal-content">
              <img
                src={selectedImage}
                alt="Producto"
                onError={(e) => { e.target.onerror = null; e.target.src = placeholderImage; }}
              />
            </div>
          </div>
        )}

        {/* ── Modal de pago ── */}
        {showPaymentModal && (
          <div className="pay-modal-overlay">
            <div className="pay-modal">
              <div className="pay-modal-header">
                <div>
                  <div className="pay-modal-title">Confirmar Venta</div>
                  <div className="pay-modal-subtitle">{displayName}</div>
                </div>
                <button className="modal-close" onClick={() => setShowPaymentModal(false)}><IconX /></button>
              </div>
              <div className="pay-modal-body">
                <div className="total-display">
                  <span className="total-display-label">Total a cobrar</span>
                  <span className="total-display-value">${cartTotal.toFixed(2)}</span>
                </div>

                <div className="form-group">
                  <label className="form-label">Tipo de comprobante</label>
                  <select className="form-control" value={receiptType} onChange={(e) => setReceiptType(e.target.value)}>
                    <option value="ticket">Ticket (Venta Rápida)</option>
                    <option value="invoice">Factura (Completa)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Método de pago</label>
                  <div className="payment-methods">
                    {[
                      { value: "cash", label: "💵 Efectivo" },
                      { value: "card", label: "💳 Tarjeta" },
                      { value: "transfer", label: "🏦 Transferencia" },
                    ].map(m => (
                      <button
                        key={m.value}
                        className={`payment-method-btn ${paymentMethod === m.value ? "selected" : ""}`}
                        onClick={() => setPaymentMethod(m.value)}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                </div>

                {paymentMethod === "cash" && (
                  <>
                    <div className="form-group" style={{ marginBottom: 6 }}>
                      <label className="form-label">Efectivo recibido</label>
                      <input
                        type="number"
                        className="form-control"
                        placeholder="0.00"
                        value={cashReceived}
                        onChange={(e) => setCashReceived(e.target.value)}
                        min={0}
                        step="0.01"
                        autoFocus
                      />
                    </div>
                    <div className={`change-display ${insufficientCash ? "change-insufficient" : ""}`}>
                      <span className="change-label">
                        {insufficientCash ? "⚠ Monto insuficiente" : "Cambio a entregar"}
                      </span>
                      <span className="change-value">
                        {insufficientCash
                          ? `-$${(cartTotal - parseFloat(cashReceived || 0)).toFixed(2)}`
                          : `$${Math.max(0, change).toFixed(2)}`}
                      </span>
                    </div>
                  </>
                )}
              </div>
              <div className="pay-modal-footer">
                <button className="btn-secondary-pay" onClick={() => setShowPaymentModal(false)}>Cancelar</button>
                <button
                  className="btn-primary-pay"
                  onClick={confirmInvoice}
                  disabled={processingPayment || (paymentMethod === "cash" && insufficientCash)}
                >
                  {processingPayment ? (
                    <><div className="spinner" style={{ width: 15, height: 15, borderWidth: 2 }} /> Procesando...</>
                  ) : (
                    <><IconCheck /> Confirmar Venta</>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default Sale;