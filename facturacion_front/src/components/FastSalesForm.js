import React, { useState } from 'react';
import BarcodeScannerInput from './BarcodeScannerInput';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';
import { showSuccessAlert, showGenericAlert } from '../herpert';

function SalesForm() {
  const [cartItems, setCartItems] = useState([]);
  const [customer, setCustomer] = useState(null);
  const navigate = useNavigate();

  const handleCancel = () => {
    navigate('/home');
  };

  // Manejar producto encontrado por el escáner
  const handleProductFound = (product) => {
    // Verificar si el producto ya está en el carrito
    const existingItemIndex = cartItems.findIndex(item => item.id === product.id);

    if (existingItemIndex !== -1) {
      // Si ya existe, aumentar cantidad
      const updatedCart = [...cartItems];
      const currentQuantity = updatedCart[existingItemIndex].quantity;
      
      // Verificar stock disponible
      if (currentQuantity >= product.stock) {
        showGenericAlert(`Stock insuficiente. Solo hay ${product.stock} unidades disponibles.`);
        return;
      }

      updatedCart[existingItemIndex].quantity += 1;
      setCartItems(updatedCart);
      // showSuccessAlert(`${product.name} agregado. Cantidad: ${updatedCart[existingItemIndex].quantity}`);
    } else {
      // Si no existe, agregar al carrito
      if (product.stock < 1) {
        showGenericAlert('Producto sin stock disponible.');
        return;
      }

      setCartItems([...cartItems, {
        id: product.id,
        name: product.name,
        price: parseFloat(product.price),
        quantity: 1,
        stock: product.stock,
        barcode: product.barcode,
        image_url: product.image_url
      }]);
      // showSuccessAlert(`${product.name} agregado al carrito.`);
    }
  };

  // Cambiar cantidad de un producto
  const handleQuantityChange = (index, newQuantity) => {
    const updatedCart = [...cartItems];
    const item = updatedCart[index];

    if (newQuantity < 1) {
      // Eliminar del carrito
      updatedCart.splice(index, 1);
    } else if (newQuantity > item.stock) {
      showGenericAlert(`Stock insuficiente. Solo hay ${item.stock} unidades disponibles.`);
      return;
    } else {
      updatedCart[index].quantity = newQuantity;
    }

    setCartItems(updatedCart);
  };

  // Eliminar producto del carrito
  const handleRemoveItem = (index) => {
    const updatedCart = [...cartItems];
    updatedCart.splice(index, 1);
    setCartItems(updatedCart);
  };

  // Calcular totales
  const calculateSubtotal = () => {
    return cartItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  };

const calculateTax = () => {
  const tax = calculateSubtotal() * 0.18;
  return Number(tax.toFixed(2));
};


  const calculateTotal = () => {
    return calculateSubtotal();
  };

  // Procesar venta
  const handleSubmitSale = async () => {
    if (cartItems.length === 0) {
      showGenericAlert('El carrito está vacío.');
      return;
    }

    try {
      const saleData = {
        customer: customer?.name || 'Despachador',  // Enviar string vacío si no hay cliente
        items: cartItems.map(item => ({
          product: item.id,
          quantity: item.quantity,
          price: item.price
        })),
        subtotal: calculateSubtotal(),
        tax: calculateTax(),
        total: calculateTotal()
      };

      await api.post('sales/', saleData);
      showSuccessAlert('Venta registrada exitosamente.');
      
      // Limpiar carrito
      setCartItems([]);
      setCustomer(null);
    } catch (error) {
      console.error('Error registrando venta:', error);
      if (error.response?.data) {
        console.error('Detalle del error:', error.response.data);
        const errorMsg = error.response.data.non_field_errors 
          ? error.response.data.non_field_errors[0]
          : 'Error al registrar la venta.';
        showGenericAlert(errorMsg);
      } else {
        showGenericAlert('Error al registrar la venta.');
      }
    }
  };

  return (
    <div className="container mt-4">
      <h2 className="mb-4">Nueva Venta</h2>

      <div className="row">
        {/* Panel izquierdo - Búsqueda y productos */}
        <div className="col-md-8">
          <div className="card mb-4">
            <div className="card-header">
              <h5 className="mb-0">Buscar Productos</h5>
            </div>
            <div className="card-body">
              <BarcodeScannerInput
                onProductFound={handleProductFound}
                placeholder="🔫 Escanea código de barras o busca por nombre..."
              />
              <small className="text-muted">
                Usa la pistola escáner o escribe para buscar productos
              </small>
            </div>
          </div>

          {/* Carrito de compras */}
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Carrito ({cartItems.length} productos)</h5>
            </div>
            <div className="card-body">
              {cartItems.length === 0 ? (
                <div className="text-center text-muted py-5">
                  <i className="bi bi-cart" style={{ fontSize: '3rem' }}>🛒</i>
                  <p className="mt-3">El carrito está vacío</p>
                  <small>Escanea o busca productos para agregarlos</small>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th>Producto</th>
                        <th>Precio</th>
                        <th>Cantidad</th>
                        <th>Subtotal</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cartItems.map((item, index) => (
                        <tr key={item.id}>
                          <td>
                            <div className="d-flex align-items-center">
                              {item.image_url && (
                                <img
                                  src={item.image_url}
                                  alt={item.name}
                                  style={{ width: '40px', height: '40px', objectFit: 'cover' }}
                                  className="rounded me-2"
                                />
                              )}
                              <div>
                                <div>{item.name}</div>
                                {item.barcode && (
                                  <small className="text-muted">{item.barcode}</small>
                                )}
                              </div>
                            </div>
                          </td>
                          <td>${item.price.toFixed(2)}</td>
                          <td>
                            <div className="input-group" style={{ width: '120px' }}>
                              <button
                                className="btn btn-outline-secondary btn-sm"
                                onClick={() => handleQuantityChange(index, item.quantity - 1)}
                              >
                                -
                              </button>
                              <input
                                type="number"
                                className="form-control form-control-sm text-center"
                                value={item.quantity}
                                onChange={(e) => handleQuantityChange(index, parseInt(e.target.value) || 1)}
                                min="1"
                                max={item.stock}
                              />
                              <button
                                className="btn btn-outline-secondary btn-sm"
                                onClick={() => handleQuantityChange(index, item.quantity + 1)}
                              >
                                +
                              </button>
                            </div>
                            <small className="text-muted">Stock: {item.stock}</small>
                          </td>
                          <td className="fw-bold">${(item.price * item.quantity).toFixed(2)}</td>
                          <td>
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => handleRemoveItem(index)}
                            >
                              🗑️
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
        </div>

        {/* Panel derecho - Resumen de venta */}
        <div className="col-md-4">
          <div className="card position-sticky" style={{ top: '20px' }}>
            <div className="card-header bg-primary text-white">
              <h5 className="mb-0">Resumen de Venta</h5>
            </div>
            <div className="card-body">
              <div className="d-flex justify-content-between mb-2">
                <span>Subtotal:</span>
                <span>${calculateSubtotal().toFixed(2)}</span>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span>ITBIS (18%):</span>
                <span>${calculateTax().toFixed(2)}</span>
              </div>
              <hr />
              <div className="d-flex justify-content-between mb-3">
                <strong>Total:</strong>
                <strong className="text-primary fs-4">${calculateTotal().toFixed(2)}</strong>
              </div>

              <button
                className="btn btn-success w-100 btn-lg"
                onClick={handleSubmitSale}
                disabled={cartItems.length === 0}
              >
                💳 Procesar Venta
              </button>

              {cartItems.length > 0 && (
                <button
                  className="btn btn-outline-danger w-100 mt-2"
                  onClick={() => setCartItems([])}
                >
                  🗑️ Vaciar Carrito
                </button>
              )}
            </div>
          </div>
         
                <button
                  className="card-text text-muted mt-3 btn btn-outline-secondary w-100"
                  onClick={() => handleCancel([])}
                >
                   Volver 
                </button>
              

        </div>
      </div>
    </div>
  );
}

export default SalesForm;