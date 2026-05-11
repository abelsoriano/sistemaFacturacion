import React, { useState, useEffect } from 'react';
import DataTable from 'react-data-table-component';
import api from '../services/api';
import { Link, useNavigate } from "react-router-dom";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import {stylesAlmacens, styles,} from "../herpert";
import Modal from 'react-bootstrap/Modal'; // Para el modal de imagen ampliada
import Image from 'react-bootstrap/Image'; // Para mejor manejo de imágenes
import "../css/ProductList.css";
import 'bootstrap-icons/font/bootstrap-icons.css';
import * as XLSX from 'xlsx';
import { FaHistory, FaFileExcel } from 'react-icons/fa';


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
  const [hoverStates, setHoverStates] = useState({
        cancel: false,
        submit: false
      });

  // Función para manejar el clic en la imagen
  const handleImageClick = (imageUrl) => {
    setSelectedImage(imageUrl);
    setShowImageModal(true);
  };

  const getStockStyle = (stock) => {
    if (stock <= 3) return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeLow };
    if (stock <= 10) return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeMedium };
    return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeHigh };
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

  const handleEdit = (id) => {
    navigate(`/productsForm/${id}`);
  };

  const handleCancel = () => {
    navigate('/home');
  };

  const handleDelete = async (id) => {
    const result = await showConfirmationAlert(
      "¿Estás seguro?",
      "Esta acción no se puede deshacer."
    );
    if (result.isConfirmed) {
      try {
        await api.delete(`/products/${id}/`);
        const updatedProducts = products.filter((product) => product.id !== id);
        setProducts(updatedProducts);
        setFilteredProducts(updatedProducts);
        showSuccessAlert("Eliminado", "El producto ha sido eliminado.");
      } catch (error) {
        showErrorAlert("Error", "No se pudo eliminar el producto.");
      }
    }
  };

  const handleFilterSubmit = async (event) => {
    event.preventDefault();
    const params = {};

    if (search) params.search = search;
    if (categoryFilter) params['category.name'] = categoryFilter;
    if (minPrice) params.min_price = minPrice;
    if (maxPrice) params.max_price = maxPrice;
    if (lowStockOnly) params.low_stock = true;

    setIsLoading(true);
    try {
      const response = await api.get('products/', { params });
      setProducts(response.data);
      setFilteredProducts(response.data);
    } catch (error) {
      console.error('Error applying filters:', error);
      showErrorAlert('Error', 'No se pudieron aplicar los filtros.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearFilters = async () => {
    setSearch('');
    setCategoryFilter('');
    setMinPrice('');
    setMaxPrice('');
    setLowStockOnly(false);
    setIsLoading(true);

    try {
      const response = await api.get('products/');
      setProducts(response.data);
      setFilteredProducts(response.data);
    } catch (error) {
      console.error('Error cleaning filters:', error);
      showErrorAlert('Error', 'No se pudieron limpiar los filtros.');
    } finally {
      setIsLoading(false);
    }
  };

  const exportToExcel = () => {
    if (!filteredProducts.length) {
      showErrorAlert('Error', 'No hay datos para exportar.');
      return;
    }

    setExporting(true);
    try {
      const worksheet = XLSX.utils.json_to_sheet(
        filteredProducts.map((product) => ({
          ID: product.id,
          Nombre: product.name,
          Categoria: product.category_name || 'Sin categoría',
          Precio: product.price,
          Stock: product.stock,
          'Stock Mínimo': product.min_stock,
          Barcode: product.barcode || 'N/D',
        }))
      );
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Productos');
      XLSX.writeFile(workbook, `productos_${new Date().toISOString().slice(0, 10)}.xlsx`);
      showSuccessAlert('Exportado', 'Los datos se han descargado en Excel.');
    } catch (error) {
      console.error('Error exporting products to Excel:', error);
      showErrorAlert('Error', 'No se pudo generar el archivo Excel.');
    } finally {
      setExporting(false);
    }
  };

  const columns = [
    {
      name: 'Imagen',
      cell: (row) => (
        <div 
          className="product-image-container"
          onClick={() => row.image_url && handleImageClick(row.image_url)}
          style={{ cursor: row.image_url ? 'pointer' : 'default' }}
        >
          <Image
            src={row.image_url || require('../assets/placeholder-product.png')}
            alt={row.name}
            className="product-thumbnail"
            thumbnail
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = require('../assets/placeholder-product.png');
            }}
          />
        </div>
      ),
      width: '80px',
      ignoreRowClick: true,
    },
    {
      name: 'Nombre',
      selector: (row) => row.name,
      sortable: true,
      cell: (row) => (
        <div className="product-name-cell">
          {row.name}
          <div className="text-muted small">{row.category_name || 'Sin categoría'}</div>
        </div>
      ),
    },
    {
      name: 'Descripción',
      selector: (row) => row.description,
      sortable: true,
      cell: (row) => (
        <div className="product-description">
          {row.description || 'Sin descripción'}
        </div>
      ),
      width: '400px',
    },
    {
      name: 'Precio',
      selector: (row) => row.price,
      sortable: true,
      cell: (row) => (
        <div className="text-end">
          <span className="fw-bold">${parseFloat(row.price).toFixed(2)}</span>
        </div>
      ),
      width: '120px',
    },
    {
      name: 'Stock',
      selector: (row) => row.stock,
      sortable: true,
      cell: (row) => (
        <div className="text-center">
          <span style={getStockStyle(row.stock)} className="stock-badge">
            {row.stock}
          </span>
        </div>
      ),
      width: '100px',
    },
    {
      name: 'Acciones',
      cell: (row) => (
        <div className="d-flex">
          <button
            className="btn btn-sm btn-outline-secondary me-2"
            onClick={() => navigate(`/products/${row.id}/history`)}
            title="Ver historial"
          >
            <FaHistory />
          </button>
          <button
            className="btn btn-sm btn-outline-primary me-2"
            onClick={() => handleEdit(row.id)}
            title="Editar"
          >
            <i className="bi bi-pencil"></i>
          </button>
          <button
            className="btn btn-sm btn-outline-danger"
            onClick={() => handleDelete(row.id)}
            title="Eliminar"
          >
            <i className="bi bi-trash"></i>
          </button>
        </div>
      ),
      width: '120px',
    },
  ];

  const customStyles = {
    rows: {
      style: {
        minHeight: '72px', // Asegurar suficiente espacio para la imagen
      },
    },
    cells: {
      style: {
        paddingTop: '8px',
        paddingBottom: '8px',
      },
    },
  };

  return (
    <div className="container mt-4">
      <Modal
        show={showImageModal}
        onHide={() => setShowImageModal(false)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Vista ampliada</Modal.Title>
        </Modal.Header>
        <Modal.Body className="text-center">
          <Image
            src={selectedImage}
            fluid
            style={{ maxHeight: "70vh" }}
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = require("../assets/placeholder-product.png");
            }}
          />
        </Modal.Body>
      </Modal>

      <div className="card">
        <div className="card-header bg-white d-flex justify-content-between align-items-center">
          <h2 className="mb-0">Lista de Productos</h2>
          
          <div>
           
          </div>

          <div >
             <button
              onClick={handleCancel}
              onMouseEnter={() =>
                setHoverStates((prev) => ({ ...prev, cancel: true }))
              }
              onMouseLeave={() =>
                setHoverStates((prev) => ({ ...prev, cancel: false }))
              }
              style={{
                ...styles.button,
                ...styles.cancelButton,
                ...(hoverStates.cancel ? styles.cancelButtonHover : {}),
              }}
            >
              Cancelar
            </button>
            
            <Link to="/productsForm" className="btn btn-primary me-2">
              <i className="bi bi-plus-circle me-2"></i>Nuevo Producto
            </Link>
          </div>
        </div>

        {lowStockCount > 0 && (
          <div className="alert alert-warning m-3 d-flex justify-content-between align-items-center">
            <div>
              <strong>⚠️ {lowStockCount} producto(s) con stock bajo.</strong>
              <div className="small text-muted">Revisa el reporte de bajo stock y toma acción inmediata.</div>
            </div>
            <button
              className="btn btn-sm btn-outline-warning"
              onClick={() => navigate('/low-stock-report')}
              title="Ver reporte de stock bajo"
            >
              Ver detalle
            </button>
          </div>
        )}

        <div className="card-body">
          <form className="row g-3 mb-4" onSubmit={handleFilterSubmit}>
            <div className="col-md-3">
              <label className="form-label">Buscar</label>
              <input
                type="text"
                className="form-control"
                placeholder="Buscar por nombre, descripción, código o categoría"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                title="Buscar texto libre en producto, descripción, categoría o código de barras"
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">Categoría</label>
              <select
                className="form-select"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                title="Filtrar por categoría"
              >
                <option value="">Todas</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.name}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label">Precio mínimo</label>
              <input
                type="number"
                className="form-control"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                min="0"
                step="0.01"
                title="Precio mínimo para filtrar"
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">Precio máximo</label>
              <input
                type="number"
                className="form-control"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                min="0"
                step="0.01"
                title="Precio máximo para filtrar"
              />
            </div>
            <div className="col-md-2 d-flex align-items-end">
              <div className="form-check">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="lowStockOnly"
                  checked={lowStockOnly}
                  onChange={(e) => setLowStockOnly(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="lowStockOnly">
                  Sólo stock bajo
                </label>
              </div>
            </div>
            <div className="col-md-1 d-flex align-items-end">
              <button type="submit" className="btn btn-primary w-100" title="Aplicar los filtros seleccionados">
                Filtrar
              </button>
            </div>
            <div className="col-md-12 d-flex justify-content-end gap-2">
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={handleClearFilters}
                title="Restaurar todos los filtros"
              >
                Limpiar filtros
              </button>
              <button
                type="button"
                className="btn btn-success"
                onClick={exportToExcel}
                disabled={exporting}
                title="Exportar la lista actual de productos a Excel"
              >
                {exporting ? 'Exportando...' : <><FaFileExcel className="me-2" />Exportar</>}
              </button>
            </div>
          </form>

          {isLoading && (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Cargando...</span>
              </div>
              <p className="mt-2">Cargando productos...</p>
            </div>
          )}

          {error && (
            <div className="alert alert-danger">
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
                <div className="py-4 text-center">
                  <i className="bi bi-exclamation-circle fs-1 text-muted"></i>
                  <p className="mt-2">No se encontraron productos</p>
                  {search && (
                    <button
                      className="btn btn-sm btn-outline-secondary mt-2"
                      onClick={() => {
                        setSearch("");
                        setFilteredProducts(products);
                      }}
                    >
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