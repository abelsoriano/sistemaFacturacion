import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import '../css/FastSalesForm.css';
import { normalizeRncInput, validateRnc } from '../utils/validators';

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
  <svg width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
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

function FastSalesForm() {
  const [cartItems, setCartItems] = useState([]);
  const [amountPaid, setAmountPaid] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clients, setClients] = useState([]);
  const [clientSearch, setClientSearch] = useState('');
  const [showClientResults, setShowClientResults] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);
  const [customerName, setCustomerName] = useState('');
  const [quickRnc, setQuickRnc] = useState('');
  const [isCreatingClient, setIsCreatingClient] = useState(false);
  const [applyItbis, setApplyItbis] = useState(true);

  const navigate = useNavigate();
  const searchContainerRef = useRef(null);
  const searchInputRef = useRef(null);
  const barcodeInputRef = useRef(null);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setCurrentUser(user);
  }, []);

  useEffect(() => {
    api.get('clients/')
      .then(response => setClients(Array.isArray(response.data) ? response.data : []))
      .catch(() => setClients([]));
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
  const tax = applyItbis ? subtotal * 0.18 : 0;
  const total = subtotal + tax;
  const paid = parseFloat(amountPaid) || 0;
  const change = paid - total;

  const quickAmounts = [500, 1000, 2000, Math.ceil(total / 100) * 100, 5000, 10000].filter((v, i, a) => a.indexOf(v) === i);
  const filteredClients = clientSearch.trim()
    ? clients.filter(client => {
        const q = clientSearch.toLowerCase();
        return (
          (client.name || '').toLowerCase().includes(q) ||
          (client.ruc_ci || '').toLowerCase().includes(q) ||
          (client.phone || '').toLowerCase().includes(q)
        );
      }).slice(0, 8)
    : [];
  const effectiveRnc = selectedClient?.ruc_ci || (customerName.trim() ? quickRnc.trim() : '');
  const effectiveEcfType = effectiveRnc ? '31' : '32';

  const clearClient = () => {
    setSelectedClient(null);
    setClientSearch('');
    setCustomerName('');
    setQuickRnc('');
  };

  const createQuickClient = async () => {
    const name = customerName.trim();
    const rnc = quickRnc.trim();
    if (!name || !rnc) {
      toast.error('Nombre y RNC son requeridos para crear cliente fiscal rápido');
      return null;
    }
    const rncError = validateRnc(rnc, { required: true, label: 'RNC del cliente' });
    if (rncError) {
      toast.error(rncError);
      return null;
    }
    setIsCreatingClient(true);
    try {
      const response = await api.post('clients/', {
        name,
        ruc_ci: rnc,
        client_type: 'occasional',
      });
      const client = response.data;
      setClients(prev => [client, ...prev.filter(item => item.id !== client.id)]);
      setSelectedClient(client);
      setClientSearch(client.name);
      toast.success('Cliente fiscal creado');
      return client;
    } catch (error) {
      toast.error(error.response?.data?.ruc_ci || error.response?.data?.name || 'No se pudo crear el cliente fiscal');
      return null;
    } finally {
      setIsCreatingClient(false);
    }
  };

  const showSaleSuccessModal = async ({ response, invoicePayload }) => {
    return new Promise((resolve) => {
      Swal.fire({
        icon: 'success',
        title: 'Venta pagada registrada',
        html: `
          <div class="pos-sale-success">
            <p><b>Total:</b> $${total.toFixed(2)}</p>
            ${change > 0 ? `<p><b>Cambio:</b> $${change.toFixed(2)}</p>` : ''}
            <p><b>Cliente:</b> ${invoicePayload.customer_name}</p>
            <p><b>Tipo e-CF:</b> E${response.data.ecf_type || invoicePayload.ecf_type}</p>
            <p><b>Factura:</b> ${response.data.invoice_number || 'N/A'}</p>
            <p><b>e-CF:</b> ${response.data.encf || 'pendiente de configuración'}</p>
            <p><b>DGII:</b> ${response.data.ecf_status || 'sin e-CF'}</p>
            <div class="pos-sale-actions">
              <button type="button" class="pos-sale-action primary" data-action="print">Imprimir ticket</button>
              <button type="button" class="pos-sale-action" data-action="view">Ver factura</button>
              <button type="button" class="pos-sale-action" data-action="new">Nueva venta</button>
              <button type="button" class="pos-sale-action ghost" data-action="close">Cerrar</button>
            </div>
          </div>
        `,
        showConfirmButton: false,
        allowOutsideClick: false,
        didOpen: () => {
          document.querySelectorAll('.pos-sale-action').forEach((button) => {
            button.addEventListener('click', () => {
              const action = button.getAttribute('data-action');
              Swal.close();
              resolve(action);
            });
          });
        },
      });
    });
  };

  const handleSubmitSale = async () => {
    if (cartItems.length === 0) { toast.error('El carrito está vacío'); return; }
    if (paid < total) { toast.error(`Faltan $${(total - paid).toFixed(2)} para completar el pago`); return; }
    if (!selectedClient && quickRnc.trim() && !customerName.trim()) {
      toast.error('Ingrese el nombre del cliente fiscal para usar RNC');
      return;
    }
    if (!selectedClient && quickRnc.trim()) {
      const rncError = validateRnc(quickRnc.trim(), { required: true, label: 'RNC del cliente' });
      if (rncError) {
        toast.error(rncError);
        return;
      }
    }
    setIsSubmitting(true);
    try {
      const customerRnc = selectedClient?.ruc_ci || quickRnc.trim();
      const invoicePayload = {
        source: 'pos',
        customer_name: selectedClient?.name || customerName.trim() || 'Consumidor Final',
        ecf_type: effectiveEcfType,
        payment_method: 'cash',
        receipt_type: 'invoice',
        status: 'paid',
        subtotal: Number(subtotal.toFixed(2)),
        tax: Number(tax.toFixed(2)),
        apply_itbis: applyItbis,
        discount: 0,
        total: Number(total.toFixed(2)),
        cash_received: Number(paid.toFixed(2)),
        change: Number(Math.max(change, 0).toFixed(2)),
        details: cartItems.map(item => ({ product_id: item.id, quantity: item.quantity, price: item.price }))
      };
      if (selectedClient?.id) {
        invoicePayload.client_id = selectedClient.id;
      }
      if (customerRnc) {
        invoicePayload.customer_rnc = customerRnc;
      }
      const response = await api.post('invoices/', invoicePayload);
      const action = await showSaleSuccessModal({ response, invoicePayload });
      setCartItems([]); setAmountPaid(''); setSearchTerm(''); setSearchResults([]); setShowResults(false); clearClient();
      if (action === 'print') {
        Swal.fire({
          icon: 'info',
          title: 'Impresión no configurada',
          text: 'La impresión de ticket directo todavía no está conectada en este POS. Puedes ver la factura y usar el flujo de impresión disponible allí.',
          confirmButtonColor: '#6C63FF',
        });
      }
      if (action === 'view' && response.data?.id) {
        navigate(`/invoices/${response.data.id}`);
        return;
      }
      if (barcodeInputRef.current) setTimeout(() => barcodeInputRef.current.focus(), 100);
    } catch (error) {
      let msg = 'Error al registrar la venta';
      if (error.response?.data) {
        const d = error.response.data;
        if (d.details) msg = d.details.map(x => Object.values(x).join(', ')).join('\n');
        else if (d.detail) msg = d.detail;
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
      <Toaster position="top-right" toastOptions={{ style: { fontSize: '13px', borderRadius: '8px' } }} />
      <div className="pos-page">
        <div className="pos-shell">

          {/* ── Panel izquierdo ── */}
          <div className="pos-left">

            {/* Topbar */}
            <div className="pos-topbar">
              <span className="pos-topbar-icon"><CartIcon /></span>
              <span className="pos-topbar-copy">
                <span className="pos-topbar-title">Nueva venta</span>
                <span className="pos-topbar-subtitle">POS de mostrador con emisión E31/E32 según cliente y RNC.</span>
              </span>
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
                        <div className="pos-result-price-wrap">
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

            <div className="pos-client-section">
              <div className="pos-client-title-row">
                <div className="pos-section-label is-compact">Cliente</div>
                <span className="pos-client-mode">E{effectiveEcfType}</span>
              </div>

              {selectedClient ? (
                <div className="pos-selected-client">
                  <strong>{selectedClient.name}</strong>
                  <div>{selectedClient.ruc_ci ? `RNC/CI: ${selectedClient.ruc_ci}` : 'Sin RNC - Consumidor Final'}</div>
                </div>
              ) : (
                <>
                  <div className="pos-client-field">
                    <input
                      className="pos-client-input"
                      placeholder="Buscar cliente existente..."
                      value={clientSearch}
                      onChange={e => { setClientSearch(e.target.value); setShowClientResults(true); }}
                      onFocus={() => setShowClientResults(true)}
                    />
                    {showClientResults && filteredClients.length > 0 && (
                      <div className="pos-client-results">
                        {filteredClients.map(client => (
                          <button
                            key={client.id}
                            className="pos-client-result"
                            onClick={() => {
                              setSelectedClient(client);
                              setClientSearch(client.name);
                              setCustomerName(client.name);
                              setQuickRnc(client.ruc_ci || '');
                              setShowClientResults(false);
                            }}
                          >
                            <div className="pos-client-result-name">{client.name}</div>
                            <div className="pos-client-result-meta">
                              {client.ruc_ci ? `RNC/CI ${client.ruc_ci}` : 'Sin RNC'}{client.phone ? ` · ${client.phone}` : ''}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <input
                    className="pos-client-input"
                    placeholder="Nombre opcional / Consumidor Final"
                    value={customerName}
                    onChange={e => setCustomerName(e.target.value)}
                  />
                  <div className="pos-client-grid is-spaced">
                    <input
                      className="pos-client-input"
                      placeholder="RNC opcional"
                      value={quickRnc}
                      onChange={e => setQuickRnc(normalizeRncInput(e.target.value))}
                      inputMode="numeric"
                      maxLength={11}
                    />
                    <button
                      className="pos-client-btn primary"
                      disabled={isCreatingClient || !customerName.trim() || !quickRnc.trim()}
                      onClick={createQuickClient}
                    >
                      {isCreatingClient ? 'Creando...' : 'Crear cliente rápido'}
                    </button>
                  </div>
                </>
              )}

              <div className="pos-client-actions">
                <button className="pos-client-btn" onClick={clearClient}>
                  Consumidor Final
                </button>
              </div>
            </div>

            <div className="pos-totals-section">
              <div className="pos-total-row">
                <span className="lbl">Subtotal</span>
                <span className="val">${subtotal.toFixed(2)}</span>
              </div>
              <div className="pos-total-row">
                <span className="lbl">ITBIS {applyItbis ? '18%' : '0%'}</span>
                <span className="val">${tax.toFixed(2)}</span>
              </div>
              <label className="pos-tax-toggle">
                <input
                  type="checkbox"
                  checked={applyItbis}
                  onChange={(event) => setApplyItbis(event.target.checked)}
                />
                <span>Aplicar ITBIS</span>
              </label>
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
                        <div className="pos-insufficient-row">
                          <span className="pos-insufficient-label">Falta por cubrir</span>
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

export default FastSalesForm;
