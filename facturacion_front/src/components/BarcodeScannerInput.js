import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

/**
 * Componente para capturar códigos de barras escaneados
 * La pistola escáner actúa como un teclado que escribe rápidamente
 */
const BarcodeScannerInput = ({ onProductFound, placeholder = "Escanea o busca producto..." }) => {
  const [searchValue, setSearchValue] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef(null);
  const scannerBufferRef = useRef('');
  const scannerTimerRef = useRef(null);

  // Detectar escaneo de código de barras
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Solo procesar si el input está enfocado
      if (document.activeElement !== inputRef.current) return;

      // Si es Enter, significa que terminó el escaneo
      if (e.key === 'Enter' && scannerBufferRef.current) {
        e.preventDefault();
        searchByBarcode(scannerBufferRef.current);
        scannerBufferRef.current = '';
        clearTimeout(scannerTimerRef.current);
        return;
      }

      // Acumular caracteres del escáner
      if (e.key.length === 1) {
        scannerBufferRef.current += e.key;
        
        // Limpiar buffer después de 100ms (los escáneres escriben muy rápido)
        clearTimeout(scannerTimerRef.current);
        scannerTimerRef.current = setTimeout(() => {
          scannerBufferRef.current = '';
        }, 100);
      }
    };

    document.addEventListener('keypress', handleKeyPress);
    return () => {
      document.removeEventListener('keypress', handleKeyPress);
      clearTimeout(scannerTimerRef.current);
    };
  }, []);

  // Buscar producto por código de barras
  const searchByBarcode = async (barcode) => {
    if (!barcode || barcode.length < 3) return;

    setIsSearching(true);
    try {
      const response = await api.get(`products/search-barcode/?barcode=${barcode}`);
      if (response.data) {
        onProductFound(response.data);
        setSearchValue('');
        setSuggestions([]);
        setShowSuggestions(false);
      }
    } catch (error) {
      console.error('Producto no encontrado:', error);
      // Buscar por nombre si no se encuentra por código de barras
      searchByName(barcode);
    } finally {
      setIsSearching(false);
    }
  };

  // Buscar producto por nombre (búsqueda manual)
  const searchByName = async (query) => {
    if (!query || query.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    try {
      const response = await api.get(`products/?search=${query}`);
      setSuggestions(response.data.slice(0, 10)); // Limitar a 10 resultados
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error buscando productos:', error);
      setSuggestions([]);
    }
  };

  // Manejar cambio en el input (búsqueda manual)
  const handleInputChange = (e) => {
    const value = e.target.value;
    setSearchValue(value);
    
    // Debounce para búsqueda por nombre
    clearTimeout(scannerTimerRef.current);
    scannerTimerRef.current = setTimeout(() => {
      if (value.length >= 2) {
        searchByName(value);
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 300);
  };

  // Seleccionar producto de las sugerencias
  const handleSelectProduct = (product) => {
    onProductFound(product);
    setSearchValue('');
    setSuggestions([]);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  // Manejar Enter manual
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && searchValue) {
      e.preventDefault();
      // Si hay sugerencias, seleccionar la primera
      if (suggestions.length > 0) {
        handleSelectProduct(suggestions[0]);
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  return (
    <div className="position-relative">
      <div className="input-group">
        <span className="input-group-text">
          {isSearching ? (
            <span className="spinner-border spinner-border-sm" role="status"></span>
          ) : (
            <i className="bi bi-upc-scan">🔍</i>
          )}
        </span>
        <input
          ref={inputRef}
          type="text"
          className="form-control"
          placeholder={placeholder}
          value={searchValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          autoComplete="off"
        />
      </div>

      {/* Sugerencias de productos */}
      {showSuggestions && suggestions.length > 0 && (
        <div 
          className="position-absolute w-100 bg-white border mt-1 rounded shadow-lg z-3"
          style={{ maxHeight: '300px', overflowY: 'auto' }}
        >
          {suggestions.map((product) => (
            <div
              key={product.id}
              className="p-3 border-bottom cursor-pointer hover-bg-light"
              onClick={() => handleSelectProduct(product)}
              style={{ cursor: 'pointer' }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f9fa'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
            >
              <div className="d-flex align-items-center">
                {product.image_url && (
                  <img
                    src={product.image_url}
                    alt={product.name}
                    style={{ width: '50px', height: '50px', objectFit: 'cover' }}
                    className="rounded me-3"
                  />
                )}
                <div className="flex-grow-1">
                  <div className="fw-bold">{product.name}</div>
                  <div className="text-muted small">
                    <span className="me-3">Precio: ${product.price}</span>
                    <span className="me-3">Stock: {product.stock}</span>
                    {product.barcode && (
                      <span className="badge bg-secondary">{product.barcode}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Mensaje cuando no hay resultados */}
      {showSuggestions && suggestions.length === 0 && searchValue.length >= 2 && (
        <div className="position-absolute w-100 bg-white border mt-1 rounded shadow-lg z-3 p-3">
          <div className="text-muted text-center">
            No se encontraron productos
          </div>
        </div>
      )}
    </div>
  );
};

export default BarcodeScannerInput;