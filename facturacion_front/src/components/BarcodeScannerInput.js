import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

/**
 * Componente para capturar códigos de barras escaneados
 * La pistola escáner actúa como un teclado que escribe rápidamente
 */
const BarcodeScannerInput = ({ 
  onProductFound, 
  onSearch,
  placeholder = "Escanea o busca producto...",
  className = "",
  autoFocus = false
}) => {
  const [searchValue, setSearchValue] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isScannerActive, setIsScannerActive] = useState(false);
  const inputRef = useRef(null);
  const scannerBufferRef = useRef('');
  const scannerTimerRef = useRef(null);
  const searchTimeoutRef = useRef(null);
  const containerRef = useRef(null);

  // Auto-focus
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [autoFocus]);

  // Cerrar sugerencias al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Detectar escaneo de código de barras
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Solo procesar si el input está enfocado
      if (document.activeElement !== inputRef.current) return;

      // Si es Enter, significa que terminó el escaneo
      if (e.key === 'Enter' && scannerBufferRef.current) {
        e.preventDefault();
        handleScannerComplete(scannerBufferRef.current);
        scannerBufferRef.current = '';
        clearTimeout(scannerTimerRef.current);
        return;
      }

      // Acumular caracteres del escáner
      if (e.key.length === 1) {
        scannerBufferRef.current += e.key;
        setIsScannerActive(true);
        
        // Limpiar buffer después de 100ms (los escáneres escriben muy rápido)
        clearTimeout(scannerTimerRef.current);
        scannerTimerRef.current = setTimeout(() => {
          // Si después de 100ms el buffer tiene algo, es escaneo manual lento
          if (scannerBufferRef.current) {
            setIsScannerActive(false);
          }
          scannerBufferRef.current = '';
        }, 100);
      }
    };

    document.addEventListener('keypress', handleKeyPress);
    return () => {
      document.removeEventListener('keypress', handleKeyPress);
      clearTimeout(scannerTimerRef.current);
      clearTimeout(searchTimeoutRef.current);
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
        // Notificar que se limpió la búsqueda
        if (onSearch) onSearch('');
      }
    } catch (error) {
      console.error('Producto no encontrado:', error);
      // Si no se encuentra por código, buscar por nombre
      if (onSearch) {
        onSearch(barcode);
      } else {
        searchByName(barcode);
      }
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
      setSuggestions(response.data.slice(0, 20)); // Aumentado a 20 resultados
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error buscando productos:', error);
      setSuggestions([]);
    }
  };

  // Manejar escaneo completo
  const handleScannerComplete = (barcode) => {
    searchByBarcode(barcode);
  };

  // Manejar cambio en el input (búsqueda manual)
  const handleInputChange = (e) => {
    const value = e.target.value;
    setSearchValue(value);
    
    // Clear previous timeout
    clearTimeout(searchTimeoutRef.current);
    
    // Si es muy corto, limpiar
    if (value.length < 1) {
      setSuggestions([]);
      setShowSuggestions(false);
      if (onSearch) onSearch('');
      return;
    }

    // Si parece un código de barras (números seguidos) y no está en modo scanner
    if (/^\d+$/.test(value) && value.length >= 6 && !isScannerActive) {
      searchTimeoutRef.current = setTimeout(() => {
        searchByBarcode(value);
      }, 300);
      return;
    }

    // Búsqueda por nombre con debounce
    searchTimeoutRef.current = setTimeout(() => {
      if (value.length >= 2) {
        // Si hay callback onSearch, usarlo
        if (onSearch) {
          onSearch(value);
          setShowSuggestions(false);
        } else {
          // Si no, usar sugerencias locales
          searchByName(value);
        }
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
    // Notificar que se limpió la búsqueda
    if (onSearch) onSearch('');
    inputRef.current?.focus();
  };

  // Manejar Enter manual
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && searchValue) {
      e.preventDefault();
      // Si hay sugerencias, seleccionar la primera
      if (suggestions.length > 0) {
        handleSelectProduct(suggestions[0]);
      } else if (onSearch) {
        // Si no hay sugerencias pero hay onSearch, disparar búsqueda
        onSearch(searchValue);
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setSearchValue('');
      if (onSearch) onSearch('');
    } else if (e.key === 'Tab' && suggestions.length > 0 && showSuggestions) {
      e.preventDefault();
      handleSelectProduct(suggestions[0]);
    }
  };

  // Manejar focus
  const handleFocus = () => {
    if (suggestions.length > 0) {
      setShowSuggestions(true);
    }
  };

  // Manejar blur (con delay para permitir clics en sugerencias)
  const handleBlur = () => {
    setTimeout(() => {
      if (!containerRef.current?.contains(document.activeElement)) {
        setShowSuggestions(false);
      }
    }, 200);
  };

  return (
    <div className="position-relative" ref={containerRef}>
      <div className="input-group">
        <span className="input-group-text bg-light">
          {isSearching ? (
            <span className="spinner-border spinner-border-sm text-primary" role="status"></span>
          ) : (
            <i className="bi bi-upc-scan text-primary">🔍</i>
          )}
        </span>
        <input
          ref={inputRef}
          type="text"
          className={`form-control ${className}`}
          placeholder={placeholder}
          value={searchValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={handleBlur}
          autoComplete="off"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck="false"
        />
        {searchValue && (
          <button
            className="btn btn-outline-secondary"
            type="button"
            onClick={() => {
              setSearchValue('');
              setSuggestions([]);
              setShowSuggestions(false);
              if (onSearch) onSearch('');
              inputRef.current?.focus();
            }}
          >
            <i className="bi bi-x"></i>
          </button>
        )}
      </div>

      {/* Estado del escáner */}
      {isScannerActive && (
        <div className="position-absolute top-100 start-0 mt-1 small text-primary">
          <i className="bi bi-upc-scan me-1"></i> Modo escáner activo...
        </div>
      )}

      {/* Sugerencias de productos (solo si no se usa onSearch externo) */}
      {!onSearch && showSuggestions && suggestions.length > 0 && (
        <div 
          className="position-absolute w-100 bg-white border border-top-0 rounded-bottom shadow-lg z-3"
          style={{ 
            maxHeight: '350px', 
            overflowY: 'auto',
            top: '100%',
            marginTop: '-1px'
          }}
        >
          <div className="small text-muted px-3 py-2 bg-light border-bottom">
            {suggestions.length} productos encontrados - Selecciona uno
          </div>
          {suggestions.map((product) => (
            <button
              key={product.id}
              type="button"
              className="w-100 text-start p-3 border-bottom hover-bg-light"
              onClick={() => handleSelectProduct(product)}
              style={{ 
                cursor: 'pointer',
                border: 'none',
                backgroundColor: 'transparent',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f9fa'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <div className="d-flex align-items-center">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.name}
                    style={{ 
                      width: '45px', 
                      height: '45px', 
                      objectFit: 'cover',
                      flexShrink: 0
                    }}
                    className="rounded me-3 border"
                  />
                ) : (
                  <div 
                    style={{ 
                      width: '45px', 
                      height: '45px',
                      flexShrink: 0,
                      backgroundColor: '#e9ecef',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '4px',
                      marginRight: '12px'
                    }}
                  >
                    <i className="bi bi-box-seam text-muted"></i>
                  </div>
                )}
                <div className="flex-grow-1" style={{ minWidth: 0 }}>
                  <div className="fw-semibold text-truncate" style={{ fontSize: '0.95rem' }}>
                    {product.name}
                  </div>
                  <div className="d-flex align-items-center mt-1 flex-wrap">
                    <span className="fw-bold text-primary me-3">
                      ${parseFloat(product.price).toFixed(2)}
                    </span>
                    <span className={`badge ${product.stock > 5 ? 'bg-success' : product.stock > 0 ? 'bg-warning' : 'bg-danger'} me-3`}>
                      Stock: {product.stock}
                    </span>
                    {product.barcode && (
                      <span className="badge bg-secondary text-truncate" style={{ maxWidth: '120px' }}>
                        {product.barcode}
                      </span>
                    )}
                  </div>
                </div>
                <div className="ms-2">
                  <i className="bi bi-plus-circle text-success"></i>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Mensaje cuando no hay resultados */}
      {!onSearch && showSuggestions && suggestions.length === 0 && searchValue.length >= 2 && (
        <div className="position-absolute w-100 bg-white border border-top-0 rounded-bottom shadow-lg z-3 p-4 text-center">
          <i className="bi bi-search text-muted mb-2" style={{ fontSize: '1.5rem' }}></i>
          <div className="text-muted">No se encontraron productos</div>
          <small className="d-block mt-1">Intenta con otro término de búsqueda</small>
        </div>
      )}
    </div>
  );
};

export default BarcodeScannerInput;