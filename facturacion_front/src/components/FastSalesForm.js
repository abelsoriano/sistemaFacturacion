import React, { useState, useEffect } from "react";
import api from "../services/api";
import { showGenericAlert, showSuccessAlert } from "../herpert";
import { Modal, Button } from "react-bootstrap";
import styles from "./Sale.module.css";
import { generatePDF } from './generatePDF';

const Sale = () => {
  // Estados para carrito
  const [cart, setCart] = useState([]);
  const [cartTotal, setCartTotal] = useState(0);
  
  // Estados para productos y búsqueda
  const [searchTerm, setSearchTerm] = useState("");
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Estados para la venta actual
  const [receiptType, setReceiptType] = useState("ticket");
  const [cashReceived, setCashReceived] = useState("");
  const [change, setChange] = useState(0);
  const [showModal, setShowModal] = useState(false);
  
  // Cliente por defecto
  const defaultCustomer = "Cliente General";

  // Cargar carrito guardado al iniciar
  useEffect(() => {
    const savedCart = localStorage.getItem("currentCart");
    if (savedCart) {
      const parsedCart = JSON.parse(savedCart);
      setCart(parsedCart);
      calculateTotal(parsedCart);
    }
  }, []);

  // Guardar carrito cuando cambia
  useEffect(() => {
    localStorage.setItem("currentCart", JSON.stringify(cart));
  }, [cart]);

  // Calcular cambio
  useEffect(() => {
    const received = parseFloat(cashReceived) || 0;
    setChange(received >= cartTotal ? received - cartTotal : 0);
  }, [cashReceived, cartTotal]);
  
  // Calcular total del carrito
  const calculateTotal = (currentCart) => {
    const total = currentCart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    setCartTotal(total);
    return total;
  };

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
    const existingItem = cart.find(item => item.id === product.id);

    let newCart;
    if (existingItem) {
      if (existingItem.quantity + 1 > product.stock) {
        showGenericAlert(`No hay suficiente stock de ${product.name}`);
        return;
      }
      newCart = cart.map(item => 
        item.id === product.id 
          ? { ...item, quantity: item.quantity + 1 } 
          : item
      );
    } else {
      if (product.stock < 1) {
        showGenericAlert(`El producto ${product.name} está agotado.`);
        return;
      }
      newCart = [...cart, { ...product, quantity: 1 }];
    }

    setCart(newCart);
    calculateTotal(newCart);
  };

  const updateQuantity = (productId, newQuantity) => {
    if (newQuantity < 1) {
      removeFromCart(productId);
      return;
    }

    const product = cart.find(item => item.id === productId);
    if (!product) return;

    if (newQuantity > product.stock) {
      showGenericAlert(`No hay suficiente stock de ${product.name}`);
      return;
    }

    const newCart = cart.map(item =>
      item.id === productId ? { ...item, quantity: newQuantity } : item
    );

    setCart(newCart);
    calculateTotal(newCart);
  };

  const removeFromCart = (productId) => {
    const newCart = cart.filter(item => item.id !== productId);
    setCart(newCart);
    calculateTotal(newCart);
  };

  // Confirmar venta
  const confirmInvoice = async () => {
    if (!receiptType || cashReceived === "") {
      showGenericAlert("Complete todos los campos antes de confirmar.");
      return;
    }
  
    if (parseFloat(cashReceived) < cartTotal) {
      showGenericAlert("Efectivo recibido insuficiente.");
      return;
    }
  
    try {
      // Guardar factura
      const invoiceData = {
        client_name: defaultCustomer,
        details: cart.map(item => ({
          product_id: item.id,
          quantity: item.quantity,
          price: item.price,
          subtotal: item.price * item.quantity,
        })),
        total: cartTotal,
        receipt_type: receiptType,
        cash_received: parseFloat(cashReceived),
        change: change,
      };
  
      const invoiceResponse = await api.post("/invoices/", invoiceData);
  
      // Guardar venta
      const saleData = {
        invoice_id: invoiceResponse.data.id,
        client_name: defaultCustomer,
        products: cart.map(item => ({
          product_id: item.id,
          quantity: item.quantity,
          price: item.price,
          subtotal: item.price * item.quantity,
        })),
        total: cartTotal,
      };
  
      await api.post("/sales/", saleData);
  
      // Limpiar carrito
      setCart([]);
      setCartTotal(0);
      setCashReceived("");
      setChange(0);
      setShowModal(false);
  
      showSuccessAlert("Venta registrada exitosamente");
      
      if (window.confirm("¿Deseas imprimir la factura?")) {
        generatePDF(invoiceData); 
      }
  
    } catch (error) {
      console.error("Error:", error.response?.data || error.message);
      showGenericAlert("No se pudo completar la transacción.");
    }
  };

  return (
    <div className={`container mt-5 ${styles.container}`}>
      <h1>Ventas de Repuestos</h1>

      {/* Barra superior */}
      <div className="d-flex justify-content-between align-items-center mb-3 p-2 bg-light rounded">
        <div>
          <span className="badge bg-primary">Cliente: {defaultCustomer}</span>
        </div>
        <div>
          <span className="fw-bold me-2">Total: ${cartTotal.toFixed(2)}</span>
          <button
            className="btn btn-sm btn-success"
            onClick={() => setShowModal(true)}
            disabled={!cart.length}
          >
            Finalizar Venta
          </button>
        </div>
      </div>

      {/* Buscador y lista de productos */}
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
                  {products.map((product) => (
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
                  {searchTerm
                    ? "No se encontraron productos"
                    : "Ingrese un término de búsqueda"}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Carrito actual */}
        <div className="col-md-5">
          <div className="card shadow-sm">
            <div className="card-header bg-success text-white">
              <h4>Carrito</h4>
            </div>
            <div className="card-body">
              {cart.length > 0 ? (
                <ul className="list-group">
                  {cart.map((item) => (
                    <li
                      key={item.id}
                      className="list-group-item d-flex justify-content-between align-items-center"
                    >
                      <div>
                        <strong>{item.name}</strong>
                        <div className="d-flex align-items-center mt-2">
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() =>
                              updateQuantity(item.id, item.quantity - 1)
                            }
                          >
                            -
                          </button>
                          <span className="mx-2">{item.quantity}</span>
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() =>
                              updateQuantity(item.id, item.quantity + 1)
                            }
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
              value={`${cartTotal.toFixed(2)}`}
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
              min={0}
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