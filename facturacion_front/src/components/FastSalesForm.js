import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';

const styles = `
  .pos-shell {
    display: grid;
    grid-template-columns: 1fr 340px;
    height: calc(100vh - 32px);
    border: 0.5px solid #e0e0e0;
    border-radius: 12px;
    overflow: hidden;
    background: #f4f5f7;
  }
  .pos-left {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    overflow: hidden;
  }
  .pos-topbar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #fff;
    border-radius: 10px;
    padding: 10px 16px;
    border: 0.5px solid #e5e7eb;
    flex-shrink: 0;
  }
  .pos-topbar-title {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    flex: 1;
  }
  .pos-user-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #6b7280;
    background: #f3f4f6;
    border-radius: 20px;
    padding: 4px 12px;
  }
  .pos-back-top {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #6b7280;
    background: transparent;
    border: 0.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 5px 12px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .pos-back-top:hover { background: #f3f4f6; }

  .pos-search-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    flex-shrink: 0;
    position: relative;
  }
  .pos-search-box {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #fff;
    border: 0.5px solid #d1d5db;
    border-radius: 8px;
    padding: 9px 12px;
    transition: border-color 0.15s;
  }
  .pos-search-box:focus-within { border-color: #1D9E75; }
  .pos-search-box svg { color: #9ca3af; flex-shrink: 0; }
  .pos-search-box input {
    border: none;
    background: transparent;
    font-size: 13px;
    color: #111827;
    outline: none;
    width: 100%;
  }
  .pos-barcode-box {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #fff;
    border: 0.5px solid #d1d5db;
    border-radius: 8px;
    padding: 9px 12px;
    transition: border-color 0.15s;
  }
  .pos-barcode-box:focus-within { border-color: #1D9E75; }
  .pos-barcode-box svg { color: #1D9E75; flex-shrink: 0; }
  .pos-barcode-box input {
    border: none;
    background: transparent;
    font-size: 13px;
    color: #111827;
    outline: none;
    width: 100%;
  }
  .pos-search-results {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    right: 50%;
    background: #fff;
    border: 0.5px solid #e5e7eb;
    border-radius: 10px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.10);
    z-index: 100;
    max-height: 280px;
    overflow-y: auto;
  }
  .pos-result-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    cursor: pointer;
    border-bottom: 0.5px solid #f3f4f6;
    transition: background 0.1s;
    width: 100%;
    text-align: left;
    background: transparent;
    border-left: none;
    border-right: none;
    border-top: none;
  }
  .pos-result-item:last-child { border-bottom: none; }
  .pos-result-item:hover { background: #f0fdf8; }
  .pos-result-name { font-size: 13px; font-weight: 500; color: #111827; }
  .pos-result-code { font-size: 11px; color: #9ca3af; margin-top: 2px; }
  .pos-result-price { font-size: 14px; font-weight: 600; color: #1D9E75; }
  .pos-result-stock-ok { background: #dcfce7; color: #166534; font-size: 10px; padding: 2px 7px; border-radius: 10px; display: inline-block; margin-top: 3px; }
  .pos-result-stock-low { background: #fef9c3; color: #854d0e; font-size: 10px; padding: 2px 7px; border-radius: 10px; display: inline-block; margin-top: 3px; }
  .pos-result-stock-none { background: #fee2e2; color: #991b1b; font-size: 10px; padding: 2px 7px; border-radius: 10px; display: inline-block; margin-top: 3px; }
  .pos-search-loading {
    padding: 20px;
    text-align: center;
    color: #6b7280;
    font-size: 13px;
  }
  .pos-search-empty {
    padding: 24px;
    text-align: center;
    color: #9ca3af;
    font-size: 13px;
  }

  .pos-cart-card {
    flex: 1;
    background: #fff;
    border-radius: 10px;
    border: 0.5px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }
  .pos-cart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 0.5px solid #f3f4f6;
    flex-shrink: 0;
  }
  .pos-cart-header-left {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #111827;
  }
  .pos-cart-badge {
    background: #1D9E75;
    color: #fff;
    font-size: 11px;
    font-weight: 500;
    border-radius: 20px;
    padding: 2px 9px;
  }
  .pos-clear-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #991b1b;
    background: #fee2e2;
    border: none;
    border-radius: 7px;
    padding: 5px 10px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .pos-clear-btn:hover { background: #fecaca; }
  .pos-cart-table-wrap {
    flex: 1;
    overflow-y: auto;
  }
  .pos-cart-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .pos-cart-table thead th {
    padding: 8px 16px;
    text-align: left;
    font-size: 10px;
    font-weight: 600;
    color: #9ca3af;
    background: #f9fafb;
    border-bottom: 0.5px solid #f3f4f6;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    position: sticky;
    top: 0;
    z-index: 1;
  }
  .pos-cart-table thead th.right { text-align: right; }
  .pos-cart-table tbody tr { border-bottom: 0.5px solid #f9fafb; }
  .pos-cart-table tbody tr:last-child { border-bottom: none; }
  .pos-cart-table tbody tr:hover { background: #f9fafb; }
  .pos-cart-table tbody td { padding: 10px 16px; vertical-align: middle; color: #111827; }
  .pos-prod-name { font-weight: 500; font-size: 13px; color: #111827; }
  .pos-prod-code { font-size: 11px; color: #9ca3af; margin-top: 2px; }
  .pos-qty-ctrl {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .pos-qty-btn {
    width: 26px; height: 26px;
    border-radius: 6px;
    border: 0.5px solid #e5e7eb;
    background: #f9fafb;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    color: #374151;
    font-size: 14px;
    transition: background 0.1s, border-color 0.1s;
    flex-shrink: 0;
  }
  .pos-qty-btn:hover { background: #e0fdf4; border-color: #6ee7b7; color: #065f46; }
  .pos-qty-input {
    width: 38px;
    text-align: center;
    font-size: 13px;
    font-weight: 600;
    color: #111827;
    border: 0.5px solid #e5e7eb;
    border-radius: 6px;
    padding: 3px 0;
    background: #fff;
    outline: none;
  }
  .pos-qty-input:focus { border-color: #1D9E75; }
  .pos-price-col { text-align: right; color: #6b7280; }
  .pos-subtotal-col { text-align: right; font-weight: 600; color: #111827; }
  .pos-del-btn {
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px;
    border-radius: 7px;
    border: 0.5px solid #f3f4f6;
    background: transparent;
    color: #d1d5db;
    cursor: pointer;
    margin-left: auto;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
  }
  .pos-del-btn:hover { background: #fee2e2; color: #991b1b; border-color: #fecaca; }

  .pos-cart-empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: #d1d5db;
    padding: 40px;
  }
  .pos-cart-empty-icon { font-size: 48px; opacity: 0.3; }
  .pos-cart-empty p { font-size: 14px; color: #9ca3af; margin: 0; }
  .pos-cart-empty small { font-size: 12px; color: #d1d5db; }

  .pos-right {
    background: #fff;
    border-left: 0.5px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .pos-summary-header {
    padding: 14px 20px 12px;
    border-bottom: 0.5px solid #f3f4f6;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .pos-summary-icon { font-size: 18px; color: #1D9E75; }
  .pos-summary-title { font-size: 14px; font-weight: 600; color: #111827; }
  .pos-totals-section {
    padding: 16px 20px;
    border-bottom: 0.5px solid #f3f4f6;
    flex-shrink: 0;
  }
  .pos-total-row {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 13px;
    padding: 4px 0;
  }
  .pos-total-row .lbl { color: #6b7280; }
  .pos-total-row .val { color: #111827; font-weight: 500; }
  .pos-total-main {
    display: flex; justify-content: space-between; align-items: center;
    padding-top: 12px;
    margin-top: 8px;
    border-top: 0.5px solid #f3f4f6;
  }
  .pos-total-main .lbl { font-size: 15px; font-weight: 600; color: #111827; }
  .pos-total-main .val { font-size: 24px; font-weight: 700; color: #0F6E56; }
  .pos-payment-section {
    padding: 16px 20px;
    border-bottom: 0.5px solid #f3f4f6;
    flex-shrink: 0;
  }
  .pos-section-label {
    font-size: 10px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
  }
  .pos-amount-wrap {
    display: flex;
    align-items: center;
    background: #f9fafb;
    border: 0.5px solid #d1d5db;
    border-radius: 8px;
    padding: 10px 14px;
    gap: 6px;
    margin-bottom: 12px;
    transition: border-color 0.15s;
  }
  .pos-amount-wrap:focus-within { border-color: #1D9E75; background: #fff; }
  .pos-currency { font-size: 17px; font-weight: 600; color: #9ca3af; }
  .pos-amount-input {
    border: none; background: transparent;
    font-size: 22px; font-weight: 600;
    color: #111827; outline: none; width: 100%;
  }
  .pos-quick-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }
  .pos-quick-btn {
    background: #f9fafb;
    border: 0.5px solid #e5e7eb;
    border-radius: 7px;
    padding: 7px 4px;
    font-size: 12px;
    font-weight: 500;
    color: #374151;
    cursor: pointer;
    text-align: center;
    transition: all 0.12s;
  }
  .pos-quick-btn:hover { background: #e0fdf4; border-color: #6ee7b7; color: #065f46; }
  .pos-change-section { padding: 14px 20px; flex-shrink: 0; }
  .pos-change-box {
    background: #f0fdf8;
    border: 0.5px solid #6ee7b7;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .pos-change-insufficient {
    background: #fff7ed;
    border: 0.5px solid #fdba74;
    border-radius: 8px;
    padding: 12px 16px;
  }
  .pos-change-lbl { font-size: 12px; color: #065f46; font-weight: 500; }
  .pos-change-val { font-size: 20px; font-weight: 700; color: #0F6E56; }
  .pos-change-missing { font-size: 13px; color: #c2410c; font-weight: 500; }
  .pos-action-section { padding: 16px 20px; margin-top: auto; flex-shrink: 0; }
  .pos-process-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: #1D9E75;
    color: #fff;
    border: none;
    border-radius: 9px;
    padding: 14px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
    letter-spacing: 0.01em;
  }
  .pos-process-btn:hover:not(:disabled) { background: #0F6E56; }
  .pos-process-btn:active:not(:disabled) { transform: scale(0.99); }
  .pos-process-btn:disabled { background: #9ca3af; cursor: not-allowed; }
  .pos-spinner {
    width: 16px; height: 16px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: #fff;
    border-radius: 50%;
    animation: pos-spin 0.6s linear infinite;
    flex-shrink: 0;
  }
  @keyframes pos-spin { to { transform: rotate(360deg); } }

  @media (max-width: 900px) {
    .pos-shell {
      grid-template-columns: 1fr;
      height: auto;
      min-height: 100vh;
    }
    .pos-right {
      border-left: none;
      border-top: 0.5px solid #e5e7eb;
    }
  }
`;

const CartIcon = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
  </svg>
);
const SearchIcon = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);
const BarcodeIcon = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" viewBox="0 0 24 24">
    <path d="M3 5v14M7 5v14M11 5v14M15 5v14M19 5v14M21 5v14M1 5v14"/>
  </svg>
);
const TrashIcon = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
  </svg>
);
const XIcon = () => (
  <svg width="11" height="11" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" viewBox="0 0 24 24">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const ReceiptIcon = () => (
  <svg width="17" height="17" fill="none" stroke="#1D9E75" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1z"/>
    <line x1="9" y1="7" x2="15" y2="7"/><line x1="9" y1="11" x2="15" y2="11"/><line x1="9" y1="15" x2="13" y2="15"/>
  </svg>
);
const CreditCardIcon = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/>
  </svg>
);
const ArrowLeftIcon = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
  </svg>
);
const UserIcon = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
  </svg>
);

function SalesForm() {
  const [cartItems, setCartItems] = useState([]);
  const [amountPaid, setAmountPaid] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();
  const searchContainerRef = useRef(null);
  const searchInputRef = useRef(null);
  const barcodeInputRef = useRef(null);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setCurrentUser(user);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const searchProducts = useCallback(async (term) => {
    if (!term.trim()) { setSearchResults([]); setShowResults(false); return; }
    setIsSearching(true);
    setShowResults(true);
    try {
      const response = await api.get(`products/?search=${term}`);
      setSearchResults(response.data.slice(0, 20));
    } catch (error) {
      toast.error('Error al buscar productos');
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => { if (searchTerm) searchProducts(searchTerm); }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm, searchProducts]);

  const addToCart = (product, quantity = 1) => {
    const existingItem = cartItems.find(item => item.id === product.id);
    if (existingItem) {
      const newQty = existingItem.quantity + quantity;
      if (newQty > product.stock) { toast.error(`Stock insuficiente. Solo hay ${product.stock} unidades.`); return; }
      setCartItems(cartItems.map(item => item.id === product.id ? { ...item, quantity: newQty } : item));
      toast.success(`Cantidad actualizada a ${newQty}`);
    } else {
      if (product.stock < quantity) { toast.error('Producto sin stock disponible'); return; }
      setCartItems([...cartItems, {
        id: product.id, name: product.name,
        price: parseFloat(product.price), quantity,
        stock: product.stock, barcode: product.barcode,
        image_url: product.image_url
      }]);
      toast.success(`${product.name} agregado`);
    }
    setSearchTerm(''); setSearchResults([]); setShowResults(false);
    if (barcodeInputRef.current) barcodeInputRef.current.focus();
  };

  const handleBarcodeScanned = async (barcode) => {
    if (!barcode || barcode.length < 3) return;
    try {
      const response = await api.get(`products/search-barcode/?barcode=${barcode}`);
      addToCart(response.data, 1);
    } catch (error) {
      toast.error(error.response?.status === 404 ? 'Producto no encontrado' : 'Error al buscar producto');
    }
  };

  const updateQuantity = (index, newQuantity) => {
    const item = cartItems[index];
    if (newQuantity < 1) { removeItem(index); return; }
    if (newQuantity > item.stock) { toast.error(`Stock insuficiente. Máximo: ${item.stock}`); return; }
    const updated = [...cartItems];
    updated[index].quantity = newQuantity;
    setCartItems(updated);
  };

  const removeItem = (index) => {
    const name = cartItems[index].name;
    Swal.fire({
      title: '¿Eliminar producto?',
      text: `¿Deseas eliminar ${name} del carrito?`,
      icon: 'question', showCancelButton: true,
      confirmButtonColor: '#ef4444', confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar'
    }).then(result => {
      if (result.isConfirmed) {
        setCartItems(cartItems.filter((_, i) => i !== index));
        toast.success('Producto eliminado');
      }
    });
  };

  const clearCart = () => {
    if (cartItems.length === 0) return;
    Swal.fire({
      title: '¿Vaciar carrito?', text: 'Se eliminarán todos los productos',
      icon: 'warning', showCancelButton: true,
      confirmButtonColor: '#ef4444', confirmButtonText: 'Sí, vaciar', cancelButtonText: 'Cancelar'
    }).then(result => {
      if (result.isConfirmed) { setCartItems([]); setAmountPaid(''); toast.success('Carrito vaciado'); }
    });
  };

  const subtotal = cartItems.reduce((s, i) => s + i.price * i.quantity, 0);
  const tax = subtotal * 0.16;
  const total = subtotal + tax;
  const paid = parseFloat(amountPaid) || 0;
  const change = paid - total;

  const quickAmounts = [500, 1000, 2000, Math.ceil(total / 100) * 100, 5000, 10000].filter((v, i, a) => a.indexOf(v) === i);

  const handleSubmitSale = async () => {
    if (cartItems.length === 0) { toast.error('El carrito está vacío'); return; }
    if (paid < total) { toast.error(`Faltan $${(total - paid).toFixed(2)} para completar el pago`); return; }
    setIsSubmitting(true);
    try {
      const saleData = {
        customer: currentUser?.username || 'Consumidor Final',
        details: cartItems.map(item => ({ product_id: item.id, quantity: item.quantity, price: item.price }))
      };
      const response = await api.post('sales/', saleData);
      await Swal.fire({
        icon: 'success', title: '¡Venta registrada!',
        html: `<p><b>Total:</b> $${total.toFixed(2)}</p>${change > 0 ? `<p><b>Cambio:</b> $${change.toFixed(2)}</p>` : ''}<p><b>Folio #:</b> ${response.data.id || 'N/A'}</p>`,
        confirmButtonColor: '#1D9E75'
      });
      if (window.confirm('¿Deseas imprimir el ticket?')) console.log('Imprimiendo...');
      setCartItems([]); setAmountPaid(''); setSearchTerm(''); setSearchResults([]); setShowResults(false);
      if (barcodeInputRef.current) setTimeout(() => barcodeInputRef.current.focus(), 100);
    } catch (error) {
      let msg = 'Error al registrar la venta';
      if (error.response?.data) {
        const d = error.response.data;
        if (d.details) msg = d.details.map(x => Object.values(x).join(', ')).join('\n');
        else if (d.error) msg = d.error;
        else if (d.non_field_errors) msg = d.non_field_errors.join(', ');
      }
      Swal.fire({ icon: 'error', title: 'Error', text: msg, confirmButtonColor: '#ef4444' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <style>{styles}</style>
      <Toaster position="top-right" toastOptions={{ style: { fontSize: '13px', borderRadius: '8px' } }} />
      <div style={{ padding: '16px', minHeight: '100vh', background: '#f4f5f7' }}>
        <div className="pos-shell">

          {/* ── Panel izquierdo ── */}
          <div className="pos-left">

            {/* Topbar */}
            <div className="pos-topbar">
              <CartIcon />
              <span className="pos-topbar-title">Nueva venta</span>
              <div className="pos-user-chip">
                <UserIcon />
                <span>{currentUser?.username || 'Usuario'}</span>
              </div>
              <button className="pos-back-top" onClick={() => navigate('/home')}>
                <ArrowLeftIcon /> Volver
              </button>
            </div>

            {/* Búsqueda y escáner */}
            <div className="pos-search-row" ref={searchContainerRef}>
              <div className="pos-search-box">
                <SearchIcon />
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Buscar producto por nombre..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
              </div>
              <div className="pos-barcode-box">
                <BarcodeIcon />
                <input
                  ref={barcodeInputRef}
                  type="text"
                  placeholder="Escanear código de barras..."
                  onKeyPress={e => { if (e.key === 'Enter') { handleBarcodeScanned(e.target.value); e.target.value = ''; } }}
                />
              </div>

              {showResults && (
                <div className="pos-search-results">
                  {isSearching ? (
                    <div className="pos-search-loading">Buscando...</div>
                  ) : searchResults.length > 0 ? (
                    searchResults.map(product => (
                      <button key={product.id} className="pos-result-item" onClick={() => addToCart(product, 1)}>
                        <div>
                          <div className="pos-result-name">{product.name}</div>
                          {product.barcode && <div className="pos-result-code">{product.barcode}</div>}
                          <span className={
                            product.stock > 10 ? 'pos-result-stock-ok' :
                            product.stock > 0 ? 'pos-result-stock-low' : 'pos-result-stock-none'
                          }>Stock: {product.stock}</span>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div className="pos-result-price">${parseFloat(product.price).toFixed(2)}</div>
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="pos-search-empty">No se encontraron productos</div>
                  )}
                </div>
              )}
            </div>

            {/* Carrito */}
            <div className="pos-cart-card">
              <div className="pos-cart-header">
                <div className="pos-cart-header-left">
                  <CartIcon />
                  Carrito
                  <span className="pos-cart-badge">{cartItems.length} {cartItems.length === 1 ? 'item' : 'items'}</span>
                </div>
                {cartItems.length > 0 && (
                  <button className="pos-clear-btn" onClick={clearCart}>
                    <TrashIcon /> Vaciar
                  </button>
                )}
              </div>

              {cartItems.length === 0 ? (
                <div className="pos-cart-empty">
                  <div className="pos-cart-empty-icon">🛒</div>
                  <p>El carrito está vacío</p>
                  <small>Busca o escanea productos para agregarlos</small>
                </div>
              ) : (
                <div className="pos-cart-table-wrap">
                  <table className="pos-cart-table">
                    <thead>
                      <tr>
                        <th>Producto</th>
                        <th>Cantidad</th>
                        <th className="right">Precio</th>
                        <th className="right">Subtotal</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {cartItems.map((item, index) => (
                        <tr key={item.id}>
                          <td>
                            <div className="pos-prod-name">{item.name}</div>
                            {item.barcode && <div className="pos-prod-code">{item.barcode}</div>}
                          </td>
                          <td>
                            <div className="pos-qty-ctrl">
                              <button className="pos-qty-btn" onClick={() => updateQuantity(index, item.quantity - 1)}>−</button>
                              <input
                                type="number"
                                className="pos-qty-input"
                                value={item.quantity}
                                onChange={e => updateQuantity(index, parseInt(e.target.value) || 1)}
                                min="1"
                                max={item.stock}
                              />
                              <button className="pos-qty-btn" onClick={() => updateQuantity(index, item.quantity + 1)}>+</button>
                            </div>
                          </td>
                          <td className="pos-price-col">${item.price.toFixed(2)}</td>
                          <td className="pos-subtotal-col">${(item.price * item.quantity).toFixed(2)}</td>
                          <td>
                            <button className="pos-del-btn" aria-label="Eliminar" onClick={() => removeItem(index)}>
                              <XIcon />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* ── Panel derecho ── */}
          <div className="pos-right">
            <div className="pos-summary-header">
              <ReceiptIcon />
              <span className="pos-summary-title">Resumen de venta</span>
            </div>

            <div className="pos-totals-section">
              <div className="pos-total-row">
                <span className="lbl">Subtotal</span>
                <span className="val">${subtotal.toFixed(2)}</span>
              </div>
              <div className="pos-total-row">
                <span className="lbl">IVA 16%</span>
                <span className="val">${tax.toFixed(2)}</span>
              </div>
              <div className="pos-total-main">
                <span className="lbl">Total</span>
                <span className="val">${total.toFixed(2)}</span>
              </div>
            </div>

            {cartItems.length > 0 && (
              <>
                <div className="pos-payment-section">
                  <div className="pos-section-label">Monto recibido</div>
                  <div className="pos-amount-wrap">
                    <span className="pos-currency">$</span>
                    <input
                      type="number"
                      className="pos-amount-input"
                      placeholder="0.00"
                      value={amountPaid}
                      onChange={e => setAmountPaid(e.target.value)}
                      step="0.01"
                      min="0"
                    />
                  </div>
                  <div className="pos-section-label">Montos rápidos</div>
                  <div className="pos-quick-grid">
                    {quickAmounts.map(amount => (
                      <button key={amount} className="pos-quick-btn" onClick={() => setAmountPaid(amount.toString())}>
                        ${amount.toLocaleString()}
                      </button>
                    ))}
                  </div>
                </div>

                {amountPaid && paid > 0 && (
                  <div className="pos-change-section">
                    {change >= 0 ? (
                      <div className="pos-change-box">
                        <span className="pos-change-lbl">Cambio</span>
                        <span className="pos-change-val">${change.toFixed(2)}</span>
                      </div>
                    ) : (
                      <div className="pos-change-insufficient">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '12px', color: '#92400e', fontWeight: 500 }}>Falta por cubrir</span>
                          <span className="pos-change-missing">${Math.abs(change).toFixed(2)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="pos-action-section">
                  <button
                    className="pos-process-btn"
                    onClick={handleSubmitSale}
                    disabled={isSubmitting || cartItems.length === 0}
                  >
                    {isSubmitting ? (
                      <><div className="pos-spinner" /> Procesando...</>
                    ) : (
                      <><CreditCardIcon /> Procesar venta</>
                    )}
                  </button>
                </div>
              </>
            )}
          </div>

        </div>
      </div>
    </>
  );
}

export default SalesForm;