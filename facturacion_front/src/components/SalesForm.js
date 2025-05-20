import React, { useState, useEffect } from "react";
import api from "../services/api";
import { showGenericAlert, showSuccessAlert, showGenerAlertSioNo } from "../herpert";
import { Modal, Button, Image, Badge } from "react-bootstrap";
import styles from "./Sale.module.css";
import { generatePDF } from './generatePDF';
import placeholderImage from '../assets/placeholder-product.png';
import "../css/SalesForm.css";

const Sale = () => {
  // Estados para clientes y carritos
  const [customer, setCustomer] = useState('');
  const [savedCarts, setSavedCarts] = useState({});
  const [activeCustomer, setActiveCustomer] = useState(null);

  // Estados para productos y búsqueda
  const [searchTerm, setSearchTerm] = useState("");
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Estados para la venta actual
  const [receiptType, setReceiptType] = useState("ticket");
  const [cashReceived, setCashReceived] = useState("");
  const [change, setChange] = useState(0);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  // Estados para imágenes
  const [showImageModal, setShowImageModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState("");

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

  // Buscar productos con imágenes
  const handleSearch = async (term) => {
    setSearchTerm(term);
    if (term.trim() === "") {
      setProducts([]);
      return;
    }
    setLoading(true);
    try {
      const response = await api.get(`/products/?search=${term}`);
      setProducts(response.data.map(product => ({
        ...product,
        image_url: product.image_url || placeholderImage
      })));
    } catch (error) {
      console.error("Error buscando productos:", error);
      showGenericAlert("Error al buscar productos");
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
      const invoiceData = {
        customer: activeCustomer,
        details: currentCart.map(item => ({
          product_id: item.id,
          products: item.name,
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
  
      const saleData = {
        invoice_id: invoiceResponse.data.id,
        customer: activeCustomer,
        products: currentCart.map(item => ({
          product_id: item.id,
          quantity: item.quantity,
          price: item.price,
          subtotal: item.price * item.quantity,
        })),
        total: currentTotal,
      };
  
      await api.post("/sales/", saleData);
  
      const updatedCarts = { ...savedCarts };
      updatedCarts[activeCustomer] = { cart: [], total: 0 };
      
      setSavedCarts(updatedCarts);
      setCashReceived("");
      setChange(0);
      setShowPaymentModal(false);
  
      showSuccessAlert(`Venta para ${activeCustomer} registrada exitosamente`);
      
      const shouldPrint = await showGenerAlertSioNo("¿Deseas imprimir la factura?");
      if (shouldPrint) {
        generatePDF(invoiceData);
      }
  
      const continueWithSameClient = await showGenerAlertSioNo(
        `¿Desea hacer otra venta para ${activeCustomer}?`
      );
      
      if (!continueWithSameClient) {
        setActiveCustomer(null);
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
    setCustomer("");
    
    if (!savedCarts[customer]) {
      setSavedCarts({
        ...savedCarts,
        [customer]: { cart: [], total: 0 }
      });
    }
  };

  // Función para mostrar imagen ampliada
  const handleImageClick = (imageUrl) => {
    if (!imageUrl || imageUrl === placeholderImage) return;
    setSelectedImage(imageUrl);
    setShowImageModal(true);
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
              onChange={(e) => setCustomer(e.target.value)} 
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
                onClick={() => setShowPaymentModal(true)}
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
                  placeholder="Buscar por nombre, código o descripción"
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                />
                {loading ? (
                  <div className="text-center py-3">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Buscando...</span>
                    </div>
                  </div>
                ) : products.length > 0 ? (
                  <div className="list-group product-search-list">
                    {products.map(product => (
                      <div
                        key={product.id}
                        className="list-group-item d-flex align-items-center"
                      >
                        <div 
                          className="product-image-thumbnail me-3"
                          onClick={() => handleImageClick(product.image_url)}
                        >
                          <Image
                            src={product.image_url}
                            alt={product.name}
                            thumbnail
                            className={product.image_url === placeholderImage ? 'placeholder-img' : ''}
                            onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = placeholderImage;
                              e.target.className = 'placeholder-img';
                            }}
                          />
                        </div>
                        <div className="flex-grow-1">
                          <div className="d-flex justify-content-between">
                            <strong>{product.name}</strong>
                            <Badge bg="secondary" className="ms-2">
                              {/* ${product.price.toFixed(2)} */}
                            </Badge>
                          </div>
                          <div className="text-muted small">
                            {product.description || 'Sin descripción'}
                          </div>
                          <div className="d-flex justify-content-between align-items-center mt-2">
                            <small className="text-muted">
                              Stock: {product.stock}
                            </small>
                            <button
                              className="btn btn-sm btn-success"
                              onClick={() => addToCart(product)}
                              disabled={product.stock < 1}
                            >
                              {product.stock < 1 ? 'Agotado' : 'Agregar'}
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted text-center py-3">
                    {searchTerm ? "No se encontraron productos" : "Ingrese un término de búsqueda"}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Carrito actual - con imágenes */}
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
                        className="list-group-item"
                      >
                        <div className="d-flex align-items-start">
                          <div 
                            className="product-image-thumbnail me-3"
                            onClick={() => handleImageClick(item.image_url || placeholderImage)}
                          >
                            <Image
                              src={item.image_url || placeholderImage}
                              alt={item.name}
                              thumbnail
                              className={!item.image_url ? 'placeholder-img' : ''}
                            />
                          </div>
                          <div className="flex-grow-1">
                            <div className="d-flex justify-content-between">
                              <strong>{item.name}</strong>
                              <span className="text-primary">
                                {/* ${(item.price * item.quantity).toFixed(2)} */}
                              </span>
                            </div>
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
                              <span className="ms-3 text-muted small">
                                {/* ${item.price.toFixed(2)} c/u */}
                              </span>
                              <button
                                className="btn btn-sm btn-danger ms-auto"
                                onClick={() => removeFromCart(item.id)}
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-center text-muted py-4">Carrito vacío</p>
                )}
                {savedCarts[activeCustomer]?.cart?.length > 0 && (
                  <div className="mt-3 text-end">
                    <h5>
                      Total: <span className="text-success">${(savedCarts[activeCustomer]?.total || 0).toFixed(2)}</span>
                    </h5>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal para imagen ampliada */}
      <Modal show={showImageModal} onHide={() => setShowImageModal(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Vista ampliada</Modal.Title>
        </Modal.Header>
        <Modal.Body className="text-center">
          <Image 
            src={selectedImage} 
            fluid 
            style={{ maxHeight: '70vh' }}
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = placeholderImage;
            }}
          />
        </Modal.Body>
      </Modal>

      {/* Modal de pago */}
      <Modal show={showPaymentModal} onHide={() => setShowPaymentModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Finalizar Venta de {activeCustomer}?</Modal.Title>
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
          <Button variant="secondary" onClick={() => setShowPaymentModal(false)}>
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