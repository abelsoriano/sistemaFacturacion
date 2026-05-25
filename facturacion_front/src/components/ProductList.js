import React, { useState, useEffect, useCallback } from 'react';
import DataTable from 'react-data-table-component';
import api from '../services/api';
import { Link, useNavigate } from "react-router-dom";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import Modal from 'react-bootstrap/Modal';
import Image from 'react-bootstrap/Image';
import * as XLSX from 'xlsx';
import { FaHistory } from 'react-icons/fa';
import '../css/ProductList.css';

/* ── pequeños componentes de UI ─────────────────────────────────── */

const SearchIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/>
    <line x1="8" y1="12" x2="16" y2="12"/>
  </svg>
);

const WarnIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);

const DownloadIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
);

const EditIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
);

const TrashIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
    <path d="M10 11v6"/><path d="M14 11v6"/>
    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/>
  </svg>
);

const ImagePlaceholder = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <circle cx="8.5" cy="8.5" r="1.5"/>
    <polyline points="21 15 16 10 5 21"/>
  </svg>
);

/* ── hook para detectar ancho de ventana ── */
const useWindowWidth = () => {
  const [width, setWidth] = useState(window.innerWidth);
  useEffect(() => {
    const handler = () => setWidth(window.innerWidth);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);
  return width;
};

/* ── componente principal ────────────────────────────────────────── */

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [lowStockCount, setLowStockCount] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [showImageModal, setShowImageModal] = useState(false);
  const [selectedImage, setSelectedImage] = useState("");
  const navigate = useNavigate();
  const windowWidth = useWindowWidth();

  // Breakpoints
  const isMobile  = windowWidth < 480;
  const isTablet  = windowWidth >= 480 && windowWidth < 768;
  const isDesktop = windowWidth >= 768;

  const handleImageClick = (imageUrl) => {
    setSelectedImage(imageUrl);
    setShowImageModal(true);
  };

  const getStockClass = (stock) => {
    if (stock <= 3)  return "pl-stock pl-stock-low";
    if (stock <= 10) return "pl-stock pl-stock-mid";
    return "pl-stock pl-stock-ok";
  };

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await api.get('categories/');
        setCategories(response.data);
      } catch (error) {
        console.error('Error fetching categories:', error);
      }
    };

    const fetchProducts = async (params = {}) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.get('products/', { params });
        setProducts(response.data);
        setFilteredProducts(response.data);
      } catch (error) {
        console.error('Error fetching products:', error);
        setError(error);
        showErrorAlert("Error", "No se pudieron cargar los productos.");
      } finally {
        setIsLoading(false);
      }
    };

    const loadLowStockCount = async () => {
      try {
        const response = await api.get('products/', { params: { low_stock: true } });
        setLowStockCount(response.data.length);
      } catch (error) {
        console.error('Error loading low stock count:', error);
      }
    };

    fetchCategories();
    fetchProducts();
    loadLowStockCount();
  }, []);

  const handleEdit   = (id) => navigate(`/productsForm/${id}`);
  const handleCancel = () => navigate('/home');

  const handleDelete = async (id) => {
    const result = await showConfirmationAlert("¿Estás seguro?", "Esta acción no se puede deshacer.");
    if (result.isConfirmed) {
      try {
        await api.delete(`/products/${id}/`);
        const updated = products.filter((p) => p.id !== id);
        setProducts(updated);
        setFilteredProducts(updated);
        showSuccessAlert("Eliminado", "El producto ha sido eliminado.");
      } catch {
        showErrorAlert("Error", "No se pudo eliminar el producto.");
      }
    }
  };

  const handleFilterSubmit = async (event) => {
    event.preventDefault();
    const params = {};
    if (search)         params.search           = search;
    if (categoryFilter) params['category.name'] = categoryFilter;
    if (minPrice)       params.min_price        = minPrice;
    if (maxPrice)       params.max_price        = maxPrice;
    if (lowStockOnly)   params.low_stock        = true;

    setIsLoading(true);
    try {
      const response = await api.get('products/', { params });
      setProducts(response.data);
      setFilteredProducts(response.data);
    } catch {
      showErrorAlert('Error', 'No se pudieron aplicar los filtros.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearFilters = async () => {
    setSearch(''); setCategoryFilter('');
    setMinPrice(''); setMaxPrice(''); setLowStockOnly(false);
    setIsLoading(true);
    try {
      const response = await api.get('products/');
      setProducts(response.data);
      setFilteredProducts(response.data);
    } catch {
      showErrorAlert('Error', 'No se pudieron limpiar los filtros.');
    } finally {
      setIsLoading(false);
    }
  };

  const exportToExcel = () => {
    if (!filteredProducts.length) { showErrorAlert('Error', 'No hay datos para exportar.'); return; }
    setExporting(true);
    try {
      const worksheet = XLSX.utils.json_to_sheet(
        filteredProducts.map((p) => ({
          ID: p.id, Nombre: p.name,
          Categoria: p.category_name || 'Sin categoría',
          Precio: p.price, Stock: p.stock,
          'Stock Mínimo': p.min_stock,
          Barcode: p.barcode || 'N/D',
        }))
      );
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Productos');
      XLSX.writeFile(workbook, `productos_${new Date().toISOString().slice(0, 10)}.xlsx`);
      showSuccessAlert('Exportado', 'Los datos se han descargado en Excel.');
    } catch {
      showErrorAlert('Error', 'No se pudo generar el archivo Excel.');
    } finally {
      setExporting(false);
    }
  };

  /* ── columnas responsivas ──
     Mobile  (< 480px):  imagen | nombre+cat+precio+stock | acciones
     Tablet  (480-768px): imagen | nombre+cat | precio | stock | acciones
     Desktop (≥ 768px):  imagen | nombre+cat | descripción | precio | stock | acciones
  ── */
  const columns = useCallback(() => {
    // Columna imagen — siempre presente
    const colImage = {
      name: '',
      width: '56px',
      ignoreRowClick: true,
      cell: (row) => (
        <div
          className="pl-thumb-wrap"
          onClick={() => row.image_url && handleImageClick(row.image_url)}
          style={{ cursor: row.image_url ? 'pointer' : 'default' }}
        >
          {row.image_url ? (
            <img src={row.image_url} alt={row.name}
              onError={(e) => { e.target.style.display = 'none'; }} />
          ) : (
            <span className="pl-thumb-placeholder"><ImagePlaceholder /></span>
          )}
        </div>
      ),
    };

    // Columna acciones — siempre presente
    const colActions = {
      name: '',
      width: isMobile ? '90px' : '110px',
      right: true,
      ignoreRowClick: true,
      cell: (row) => (
        <div className="pl-actions">
          <button className="pl-btn-icon"
            onClick={() => navigate(`/products/${row.id}/history`)} title="Ver historial">
            <FaHistory size={12} />
          </button>
          <button className="pl-btn-icon pl-btn-edit"
            onClick={() => handleEdit(row.id)} title="Editar">
            <EditIcon />
          </button>
          <button className="pl-btn-icon pl-btn-delete"
            onClick={() => handleDelete(row.id)} title="Eliminar">
            <TrashIcon />
          </button>
        </div>
      ),
    };

    /* ── MOBILE: nombre compacto con precio y stock inline ── */
    if (isMobile) {
      return [
        colImage,
        {
          name: 'Producto',
          grow: 1,
          wrap: true,
          cell: (row) => (
            <div className="pl-name-cell">
              <p className="pl-name">{row.name}</p>
              <span className="pl-cat">{row.category_name || 'Sin categoría'}</span>
              <div className="pl-mobile-meta">
                <span className="pl-price">
                  ${parseFloat(row.price).toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className={getStockClass(row.stock)}>{row.stock}</span>
              </div>
            </div>
          ),
        },
        colActions,
      ];
    }

    /* ── TABLET: nombre | precio | stock | acciones ── */
    if (isTablet) {
      return [
        colImage,
        {
          name: 'Nombre',
          selector: (row) => row.name,
          sortable: true,
          grow: 2,
          wrap: true,
          cell: (row) => (
            <div className="pl-name-cell">
              <p className="pl-name">{row.name}</p>
              <span className="pl-cat">{row.category_name || 'Sin categoría'}</span>
            </div>
          ),
        },
        {
          name: 'Precio',
          selector: (row) => row.price,
          sortable: true,
          width: '110px',
          right: true,
          cell: (row) => (
            <span className="pl-price">
              ${parseFloat(row.price).toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          ),
        },
        {
          name: 'Stock',
          selector: (row) => row.stock,
          sortable: true,
          width: '80px',
          center: true,
          cell: (row) => <span className={getStockClass(row.stock)}>{row.stock}</span>,
        },
        colActions,
      ];
    }

    /* ── DESKTOP: tabla completa ── */
    return [
      colImage,
      {
        name: 'Nombre',
        selector: (row) => row.name,
        sortable: true,
        grow: 2,
        wrap: true,
        cell: (row) => (
          <div className="pl-name-cell">
            <p className="pl-name">{row.name}</p>
            <span className="pl-cat">{row.category_name || 'Sin categoría'}</span>
          </div>
        ),
      },
      {
        name: 'Descripción',
        selector: (row) => row.description,
        sortable: true,
        grow: 2,
        wrap: true,
        cell: (row) => row.description
          ? <span className="pl-desc">{row.description}</span>
          : <span className="pl-desc-empty">Sin descripción</span>,
      },
      {
        name: 'Precio',
        selector: (row) => row.price,
        sortable: true,
        width: '130px',
        right: true,
        cell: (row) => (
          <span className="pl-price">
            ${parseFloat(row.price).toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        ),
      },
      {
        name: 'Stock',
        selector: (row) => row.stock,
        sortable: true,
        width: '90px',
        center: true,
        cell: (row) => <span className={getStockClass(row.stock)}>{row.stock}</span>,
      },
      colActions,
    ];
  }, [isMobile, isTablet, isDesktop])(); // se invoca inmediatamente para obtener el array

  const customStyles = {
    rows:  { style: { minHeight: '58px' } },
    cells: { style: { paddingTop: '10px', paddingBottom: '10px' } },
  };

  /* ── render ── */
  return (
    <div className="pl-page">

      {/* Modal imagen */}
      <Modal show={showImageModal} onHide={() => setShowImageModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title style={{ fontSize: 15, fontWeight: 600 }}>Vista ampliada</Modal.Title>
        </Modal.Header>
        <Modal.Body className="text-center">
          <Image src={selectedImage} fluid style={{ maxHeight: '70vh' }} />
        </Modal.Body>
      </Modal>

      <div className="pl-card">

        {/* ── Encabezado ── */}
        <div className="pl-header">
          <h2>Lista de productos</h2>
          <div className="pl-header-actions">
            <button onClick={handleCancel} className="pl-btn pl-btn-ghost">
              Cancelar
            </button>
            <Link to="/productsForm" className="pl-btn pl-btn-primary">
              <PlusIcon /> Nuevo producto
            </Link>
          </div>
        </div>

        {/* ── Alerta stock bajo ── */}
        {lowStockCount > 0 && (
          <div className="pl-alert">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ color: 'var(--pl-amber)', display: 'flex' }}><WarnIcon /></span>
              <div className="pl-alert-text">
                <strong>{lowStockCount} producto(s) con stock bajo.</strong>
                <span>Revisa el reporte de bajo stock y toma acción inmediata.</span>
              </div>
            </div>
            <button className="pl-btn-alert" onClick={() => navigate('/low-stock-report')}>
              Ver detalle
            </button>
          </div>
        )}

        {/* ── Filtros ── */}
        <form className="pl-filters" onSubmit={handleFilterSubmit}>
          <div className="pl-filter-grid">

            <div className="pl-form-group">
              <label className="pl-label">Buscar</label>
              <div className="pl-input-wrap">
                <span className="pl-input-icon"><SearchIcon /></span>
                <input
                  type="text"
                  className="pl-input pl-input-search"
                  placeholder="Nombre, descripción, código…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            <div className="pl-form-group">
              <label className="pl-label">Categoría</label>
              <select className="pl-select" value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}>
                <option value="">Todas</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.name}>{c.name}</option>
                ))}
              </select>
            </div>

            <div className="pl-form-group">
              <label className="pl-label">Precio mínimo</label>
              <input type="number" className="pl-input" placeholder="$0"
                value={minPrice} onChange={(e) => setMinPrice(e.target.value)}
                min="0" step="0.01" />
            </div>

            <div className="pl-form-group">
              <label className="pl-label">Precio máximo</label>
              <input type="number" className="pl-input" placeholder="$∞"
                value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)}
                min="0" step="0.01" />
            </div>

            <div className="pl-form-group">
              <label className="pl-label" style={{ opacity: 0 }}>_</label>
              <button type="submit" className="pl-btn pl-btn-primary" style={{ width: '100%' }}>
                Filtrar
              </button>
            </div>
          </div>

          <div className="pl-filter-row">
            <label className="pl-checkbox-label">
              <input type="checkbox" checked={lowStockOnly}
                onChange={(e) => setLowStockOnly(e.target.checked)} />
              Sólo stock bajo
            </label>
            <div className="pl-filter-actions">
              <button type="button" className="pl-btn pl-btn-outline" onClick={handleClearFilters}>
                Limpiar filtros
              </button>
              <button type="button" className="pl-btn pl-btn-success"
                onClick={exportToExcel} disabled={exporting}>
                <DownloadIcon />
                {exporting ? 'Exportando…' : 'Exportar'}
              </button>
            </div>
          </div>
        </form>

        {/* ── Cuerpo ── */}
        <div className="pl-table-wrap">
          {isLoading && (
            <div className="pl-loading">
              <div className="pl-spinner" />
              <span style={{ fontSize: 13, color: 'var(--pl-text-secondary)' }}>Cargando productos…</span>
            </div>
          )}

          {error && !isLoading && (
            <div className="pl-error">
              Error al cargar los productos: {error.message}
            </div>
          )}

          {!isLoading && !error && (
            <DataTable
              columns={columns}
              data={filteredProducts}
              pagination
              paginationPerPage={10}
              paginationRowsPerPageOptions={[5, 10, 15, 20]}
              highlightOnHover
              striped
              responsive
              customStyles={customStyles}
              noDataComponent={
                <div className="pl-empty">
                  <div className="pl-empty-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8"/>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                  </div>
                  <p>No se encontraron productos</p>
                  {search && (
                    <button className="pl-btn pl-btn-outline"
                      onClick={() => { setSearch(""); setFilteredProducts(products); }}>
                      Limpiar búsqueda
                    </button>
                  )}
                </div>
              }
            />
          )}
        </div>

      </div>
    </div>
  );
};

export default ProductList;