// components/HomeConfig.js
import React, { useState, useEffect } from 'react';
import { FaEye, FaEyeSlash, FaSave, FaTimes, FaCog, FaArrowUp, FaArrowDown } from 'react-icons/fa';

function HomeConfig({ isOpen, onClose, onSave }) {
  const [visibleItems, setVisibleItems] = useState({});
  const [tempConfig, setTempConfig] = useState({});
  const [itemOrder, setItemOrder] = useState([]);

  // Opciones que se pueden configurar
  const configurableItems = [
    { id: 'statsCards', label: 'Tarjetas de Estadísticas', category: 'general', type: 'section' },
    { id: 'searchBar', label: 'Barra de Búsqueda', category: 'general', type: 'section' },
    { id: 'quickLinks', label: 'Enlaces Rápidos', category: 'general', type: 'section' },
    
    { id: 'inventoryCategory', label: 'Categoría Inventario', category: 'categories', type: 'category' },
    { id: 'salesCategory', label: 'Categoría Ventas', category: 'categories', type: 'category' },
    { id: 'servicesCategory', label: 'Categoría Servicios', category: 'categories', type: 'category' },
    
    { id: 'products', label: 'Productos', category: 'modules', type: 'module', parent: 'inventoryCategory' },
    { id: 'categories', label: 'Categorías', category: 'modules', type: 'module', parent: 'inventoryCategory' },
    { id: 'warehouse', label: 'Almacén', category: 'modules', type: 'module', parent: 'inventoryCategory' },
    { id: 'sales', label: 'Ventas', category: 'modules', type: 'module', parent: 'salesCategory' },
    { id: 'fastSales', label: 'Venta Rápida', category: 'modules', type: 'module', parent: 'salesCategory' },
    { id: 'invoicing', label: 'Facturación', category: 'modules', type: 'module', parent: 'salesCategory' },
    { id: 'labour', label: 'Mano de Obra', category: 'modules', type: 'module', parent: 'servicesCategory' }
  ];

  useEffect(() => {
    if (isOpen) {
      // Cargar configuración guardada
      const savedConfig = JSON.parse(localStorage.getItem('homeConfig') || '{}');
      const savedOrder = JSON.parse(localStorage.getItem('homeItemOrder') || '[]');
      
      setVisibleItems(savedConfig);
      setTempConfig(savedConfig);
      
      // Si no hay orden guardado, usar orden por defecto
      if (savedOrder.length === 0) {
        const defaultOrder = configurableItems
          .filter(item => item.type === 'category')
          .map(item => item.id);
        setItemOrder(defaultOrder);
      } else {
        setItemOrder(savedOrder);
      }
    }
  }, [isOpen]);

  const toggleItem = (itemId) => {
    setTempConfig(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const moveItem = (itemId, direction) => {
    setItemOrder(prev => {
      const newOrder = [...prev];
      const currentIndex = newOrder.indexOf(itemId);
      
      if (direction === 'up' && currentIndex > 0) {
        [newOrder[currentIndex], newOrder[currentIndex - 1]] = 
        [newOrder[currentIndex - 1], newOrder[currentIndex]];
      } else if (direction === 'down' && currentIndex < newOrder.length - 1) {
        [newOrder[currentIndex], newOrder[currentIndex + 1]] = 
        [newOrder[currentIndex + 1], newOrder[currentIndex]];
      }
      
      return newOrder;
    });
  };

  const handleSave = () => {
    setVisibleItems(tempConfig);
    localStorage.setItem('homeConfig', JSON.stringify(tempConfig));
    localStorage.setItem('homeItemOrder', JSON.stringify(itemOrder));
    onSave(tempConfig, itemOrder);
    onClose();
  };

  const handleReset = () => {
    const defaultConfig = {};
    configurableItems.forEach(item => {
      defaultConfig[item.id] = true;
    });
    setTempConfig(defaultConfig);
    
    const defaultOrder = configurableItems
      .filter(item => item.type === 'category')
      .map(item => item.id);
    setItemOrder(defaultOrder);
  };

  if (!isOpen) return null;

  const categories = configurableItems.filter(item => item.type === 'category');
  const modules = configurableItems.filter(item => item.type === 'module');
  const sections = configurableItems.filter(item => item.type === 'section');

  return (
    <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              <FaCog className="me-2" />
              Configurar Dashboard
            </h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          
          <div className="modal-body">
            <p className="text-muted mb-4">
              Selecciona qué elementos quieres mostrar u ocultar en el dashboard y organiza el orden.
            </p>

            {/* Secciones generales */}
            <div className="mb-4">
              <h6 className="text-uppercase text-muted border-bottom pb-2 mb-3">
                Elementos Generales
              </h6>
              <div className="row">
                {sections.map(item => (
                  <div key={item.id} className="col-md-6 mb-3">
                    <div className="d-flex justify-content-between align-items-center p-3 border rounded">
                      <span>{item.label}</span>
                      <button
                        type="button"
                        className={`btn btn-sm ${tempConfig[item.id] !== false ? 'btn-success' : 'btn-secondary'}`}
                        onClick={() => toggleItem(item.id)}
                      >
                        {tempConfig[item.id] !== false ? <FaEye /> : <FaEyeSlash />}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Orden de categorías */}
            <div className="mb-4">
              <h6 className="text-uppercase text-muted border-bottom pb-2 mb-3">
                Orden de Categorías
              </h6>
              <div className="list-group">
                {itemOrder.map((categoryId, index) => {
                  const category = categories.find(cat => cat.id === categoryId);
                  if (!category) return null;
                  
                  return (
                    <div key={category.id} className="list-group-item d-flex justify-content-between align-items-center">
                      <div className="d-flex align-items-center">
                        <button
                          type="button"
                          className={`btn btn-sm me-3 ${tempConfig[category.id] !== false ? 'btn-success' : 'btn-secondary'}`}
                          onClick={() => toggleItem(category.id)}
                        >
                          {tempConfig[category.id] !== false ? <FaEye /> : <FaEyeSlash />}
                        </button>
                        <span>{category.label}</span>
                      </div>
                      <div>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary me-1"
                          disabled={index === 0}
                          onClick={() => moveItem(category.id, 'up')}
                        >
                          <FaArrowUp />
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary"
                          disabled={index === itemOrder.length - 1}
                          onClick={() => moveItem(category.id, 'down')}
                        >
                          <FaArrowDown />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Módulos por categoría */}
            <div className="mb-4">
              <h6 className="text-uppercase text-muted border-bottom pb-2 mb-3">
                Módulos
              </h6>
              {categories.map(category => (
                <div key={category.id} className="mb-3">
                  <h6 className="fw-bold text-primary">{category.label}</h6>
                  <div className="row">
                    {modules
                      .filter(module => module.parent === category.id)
                      .map(module => (
                        <div key={module.id} className="col-md-6 mb-2">
                          <div className="d-flex justify-content-between align-items-center p-2 border rounded">
                            <small>{module.label}</small>
                            <button
                              type="button"
                              className={`btn btn-sm ${tempConfig[module.id] !== false ? 'btn-success' : 'btn-secondary'}`}
                              onClick={() => toggleItem(module.id)}
                            >
                              {tempConfig[module.id] !== false ? <FaEye /> : <FaEyeSlash />}
                            </button>
                          </div>
                        </div>
                      ))
                    }
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline-secondary" onClick={handleReset}>
              Restablecer
            </button>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              <FaTimes className="me-1" />
              Cancelar
            </button>
            <button type="button" className="btn btn-primary" onClick={handleSave}>
              <FaSave className="me-1" />
              Guardar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomeConfig;