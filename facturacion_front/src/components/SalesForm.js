import React, { useState, useEffect } from "react";
import api from "../services/api";
import { showGenericAlert, showSuccessAlert } from "../herpert";
import { Modal, Button } from "react-bootstrap";
import styles from "./Sale.module.css";
import { generatePDF } from './generatePDF';

const Sale = () => {
  // Estados para clientes y carritos
  const [customer, setcustomer] = useState('');
  const [savedCarts, setSavedCarts] = useState({}); // { "Nombre": {cart: [], total: 0} }
  const [activeCustomer, setActiveCustomer] = useState(null);

  // Estados para productos y búsqueda
  const [searchTerm, setSearchTerm] = useState("");
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Estados para la venta actual
  const [receiptType, setReceiptType] = useState("ticket");
  const [cashReceived, setCashReceived] = useState("");
  const [change, setChange] = useState(0);
  const [showModal, setShowModal] = useState(false);

  // Cargar carritos guardados al iniciar
  useEffect(() => {
    const saved = localStorage.getItem("savedCarts");
    if (saved) setSavedCarts(JSON.parse(saved));
  }, []);

  // Guardar carritos cuando cambian
  useEffect(() => {
    localStorage.setItem("savedCarts", JSON.stringify(savedCarts));
  }, [savedCarts]);

  // Calcular cambio
  useEffect(() => {
    if (!activeCustomer) return;
    const received = parseFloat(cashReceived) || 0;
    const currentTotal = savedCarts[activeCustomer]?.total || 0;
    setChange(received >= currentTotal ? received - currentTotal : 0);
  }, [cashReceived, activeCustomer, savedCarts]);

  // Buscar productos
  const handleSearch = async (term) => {
    setSearchTerm(term);
    if (term.trim() === "") {
      setProducts([]);
      return;
    }
    setLoading(true);
    try {
      const response = await api.get(`/products/?search=${term}`);
      setProducts(response.data);
    } catch (error) {
      console.error("Error buscando productos:", error);
    } finally {
      setLoading(false);
    }
  };

  // Manejo del carrito
  const addToCart = (product) => {
    if (!activeCustomer) return;
    
    const currentCart = savedCarts[activeCustomer]?.cart || [];
    const existingItem = currentCart.find(item => item.id === product.id);

    let newCart;
    if (existingItem) {
      if (existingItem.quantity + 1 > product.stock) {
        showGenericAlert(`No hay suficiente stock de ${product.name}`);
        return;
      }
      newCart = currentCart.map(item => 
        item.id === product.id 
          ? { ...item, quantity: item.quantity + 1 } 
          : item
      );
    } else {
      if (product.stock < 1) {
        showGenericAlert(`El producto ${product.name} está agotado.`);
        return;
      }
      newCart = [...currentCart, { ...product, quantity: 1 }];
    }

    const newTotal = newCart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    setSavedCarts({
      ...savedCarts,
      [activeCustomer]: {
        cart: newCart,
        total: newTotal
      }
    });
  };

  const updateQuantity = (productId, newQuantity) => {
    if (!activeCustomer) return;
    
    const currentCart = savedCarts[activeCustomer]?.cart || [];
    
    if (newQuantity < 1) {
      removeFromCart(productId);
      return;
    }

    const product = currentCart.find(item => item.id === productId);
    if (!product) return;

    if (newQuantity > product.stock) {
      showGenericAlert(`No hay suficiente stock de ${product.name}`);
      return;
    }

    const newCart = currentCart.map(item =>
      item.id === productId ? { ...item, quantity: newQuantity } : item
    );

    const newTotal = newCart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    setSavedCarts({
      ...savedCarts,
      [activeCustomer]: {
        cart: newCart,
        total: newTotal
      }
    });
  };

  const removeFromCart = (productId) => {
    if (!activeCustomer) return;
    
    const currentCart = savedCarts[activeCustomer]?.cart || [];
    const newCart = currentCart.filter(item => item.id !== productId);
    const newTotal = newCart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    setSavedCarts({
      ...savedCarts,
      [activeCustomer]: {
        cart: newCart,
        total: newTotal
      }
    });
  };

  // Confirmar venta
  const confirmInvoice = async () => {
    if (!activeCustomer) return;
    
    if (!receiptType || cashReceived === "") {
      showGenericAlert("Complete todos los campos antes de confirmar.");
      return;
    }
  
    const currentCart = savedCarts[activeCustomer]?.cart || [];
    const currentTotal = savedCarts[activeCustomer]?.total || 0;
  
    if (parseFloat(cashReceived) < currentTotal) {
      showGenericAlert("Efectivo recibido insuficiente.");
      return;
    }
  
    try {
      // Guardar factura
      const invoiceData = {
        client_name: activeCustomer,
        details: currentCart.map(item => ({
          product_id: item.id,
          quantity: item.quantity,
          price: item.price,
          subtotal: item.price * item.quantity,
        })),
        total: currentTotal,
        receipt_type: receiptType,
        cash_received: parseFloat(cashReceived),
        change: change,
      };
  
      const invoiceResponse = await api.post("/invoices/", invoiceData);
  
      // Guardar venta
      const saleData = {
        invoice_id: invoiceResponse.data.id,
        client_name: activeCustomer,
        products: currentCart.map(item => ({
          product_id: item.id,
          quantity: item.quantity,
          price: item.price,
          subtotal: item.price * item.quantity,
        })),
        total: currentTotal,
      };
  
      await api.post("/sales/", saleData);
  
      // PARTE CORREGIDA - Solo limpia el carrito actual
      const updatedCarts = { ...savedCarts }; // Copia todos los carritos
      updatedCarts[activeCustomer] = { cart: [], total: 0 }; // Solo vacía el carrito actual
      
      setSavedCarts(updatedCarts); // Actualiza el estado
      setCashReceived("");
      setChange(0);
      setShowModal(false);
  
      showSuccessAlert(`Venta para ${activeCustomer} registrada exitosamente`);
      
      if (window.confirm("¿Deseas imprimir la factura?")) {
        generatePDF(invoiceData); 
      }
  
      // Preguntar si quiere seguir con el mismo cliente
      const continueWithSameClient = window.confirm(
        `¿Desea hacer otra venta para ${activeCustomer}?`
      );
      
      if (!continueWithSameClient) {
        setActiveCustomer(null); // Volver a selección de cliente
      }
  
    } catch (error) {
      console.error("Error:", error.response?.data || error.message);
      showGenericAlert("No se pudo completar la transacción.");
    }
  };

  // Iniciar nueva venta
  const startNewSale = () => {
    if (!customer.trim()) {
      showGenericAlert("Ingrese un nombre válido");
      return;
    }
    setActiveCustomer(customer);
    setcustomer("");
    
    // Inicializar carrito si no existe
    if (!savedCarts[customer]) {
      setSavedCarts({
        ...savedCarts,
        [customer]: { cart: [], total: 0 }
      });
    }
  };

  return (
    <div className={`container mt-5 ${styles.container}`}>
      <h1>Ventas de Repuestos</h1>

      {/* Selección de cliente */}
      {!activeCustomer ? (
        <div className="card shadow-sm mb-4">
          <div className="card-header bg-info text-white">
            <h4>Registrar Cliente/Mecánico</h4>
          </div>
          <div className="card-body">
            <input
              type="text"
              className="form-control mb-2"
              placeholder="Nombre del cliente"
              value={customer}
              onChange={(e) => setcustomer(e.target.value)} 
            />
            <button
              className="btn btn-primary"
              onClick={startNewSale}
            >
              Iniciar Venta
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Barra de cliente activo */}
          <div className="d-flex justify-content-between align-items-center mb-3 p-2 bg-light rounded">
            <div>
              <span className="badge bg-primary">Cliente: {activeCustomer}</span>
              <button 
                className="btn btn-sm btn-outline-danger ms-2"
                onClick={() => setActiveCustomer(null)}
              >
                Cambiar Cliente
              </button>
            </div>
            <div>
              <span className="fw-bold me-2">
                Total: ${(savedCarts[activeCustomer]?.total || 0).toFixed(2)}
              </span>
              <button
                className="btn btn-sm btn-success"
                onClick={() => setShowModal(true)}
                disabled={!savedCarts[activeCustomer]?.cart?.length}
              >
                Finalizar Venta
              </button>
            </div>
          </div>

          {/* Lista de clientes activos */}
          {Object.keys(savedCarts).filter(name => name !== activeCustomer).length > 0 && (
            <div className="mb-3">
              <small className="text-muted">Ventas activas:</small>
              {Object.keys(savedCarts)
                .filter(name => name !== activeCustomer && savedCarts[name].cart.length > 0)
                .map(name => (
                  <button
                    key={name}
                    className="btn btn-sm btn-outline-secondary me-1 mb-1"
                    onClick={() => setActiveCustomer(name)}
                  >
                    {name} ({savedCarts[name].cart.length})
                  </button>
                ))}
            </div>
          )}
        </>
      )}

      {/* Buscador y lista de productos */}
      {activeCustomer && (
        <div className="row">
          <div className="col-md-7">
            <div className="card shadow-sm">
              <div className="card-header bg-primary text-white">
                <h3>Buscar Producto</h3>
              </div>
              <div className="card-body">
                <input
                  type="text"
                  className="form-control mb-3"
                  placeholder="Buscar por nombre o código"
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                />
                {loading ? (
                  <div className="text-center">Buscando...</div>
                ) : products.length > 0 ? (
                  <div className="list-group">
                    {products.map(product => (
                      <div
                        key={product.id}
                        className="list-group-item d-flex justify-content-between align-items-center"
                      >
                        <div>
                          <strong>{product.name}</strong>
                          <div className="text-muted small">
                            {/* ${product.price.toFixed(2)} | Stock: {product.stock} */}
                          </div>
                        </div>
                        <button
                          className="btn btn-sm btn-success"
                          onClick={() => addToCart(product)}
                        >
                          Agregar
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted text-center">
                    {searchTerm ? "No se encontraron productos" : "Ingrese un término de búsqueda"}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Carrito actual */}
          <div className="col-md-5">
            <div className="card shadow-sm">
              <div className="card-header bg-success text-white">
                <h4>Carrito de {activeCustomer}</h4>
              </div>
              <div className="card-body">
                {savedCarts[activeCustomer]?.cart?.length > 0 ? (
                  <ul className="list-group">
                    {savedCarts[activeCustomer].cart.map(item => (
                      <li
                        key={item.id}
                        className="list-group-item d-flex justify-content-between align-items-center"
                      >
                        <div>
                          <strong>{item.name}</strong>
                          <div className="d-flex align-items-center mt-2">
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => updateQuantity(item.id, item.quantity - 1)}
                            >
                              -
                            </button>
                            <span className="mx-2">{item.quantity}</span>
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => updateQuantity(item.id, item.quantity + 1)}
                            >
                              +
                            </button>
                            <span className="ms-3">
                              ${(item.price * item.quantity).toFixed(2)}
                            </span>
                          </div>
                        </div>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => removeFromCart(item.id)}
                        >
                          ✕
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-center text-muted">Carrito vacío</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de pago */}
      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Finalizar Venta</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div className="mb-3">
            <label>Tipo de comprobante:</label>
            <select
              className="form-control"
              value={receiptType}
              onChange={(e) => setReceiptType(e.target.value)}
            >
              <option value="ticket">Ticket</option>
              <option value="factura">Factura</option>
            </select>
          </div>
          <div className="mb-3">
            <label>Total a pagar:</label>
            <input
              type="text"
              className="form-control"
              value={`$${(savedCarts[activeCustomer]?.total || 0).toFixed(2)}`}
              readOnly
            />
          </div>
          <div className="mb-3">
            <label>Efectivo recibido:</label>
            <input
              type="number"
              className="form-control"
              value={cashReceived}
              onChange={(e) => setCashReceived(e.target.value)}
              min={savedCarts[activeCustomer]?.total || 0}
            />
          </div>
          <div className="mb-3">
            <label>Cambio:</label>
            <input
              type="text"
              className="form-control"
              value={`$${change.toFixed(2)}`}
              readOnly
            />
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={confirmInvoice}>
            Confirmar Venta
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default Sale;