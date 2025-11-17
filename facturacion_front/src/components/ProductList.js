import React, { useState, useEffect } from 'react';
import DataTable from 'react-data-table-component';
import api from '../services/api';
import { Link } from "react-router-dom";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import { useNavigate } from 'react-router-dom';
import {stylesAlmacens, styles,} from "../herpert";
import Modal from 'react-bootstrap/Modal'; // Para el modal de imagen ampliada
import Image from 'react-bootstrap/Image'; // Para mejor manejo de imágenes
import "../css/ProductList.css";
import 'bootstrap-icons/font/bootstrap-icons.css';
// import { AlignCenter } from 'lucide-react';

// import {stylesAlmacens, styles, showConfirmationAlert, showSuccessAlert, showErrorAlert} from "../herpert";

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
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
    const fetchProducts = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.get('products/');
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

    fetchProducts();
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

  const handleSearch = (event) => {
    const searchTerm = event.target.value.toLowerCase();
    setSearch(searchTerm);
    const filtered = products.filter(
      (product) =>
        product.name.toLowerCase().includes(searchTerm) ||
        (product.description && product.description.toLowerCase().includes(searchTerm)) ||
        (product.category_name && product.category_name.toLowerCase().includes(searchTerm)) ||
        (product.price && product.price.toString().includes(searchTerm)) ||
        (product.stock && product.stock.toString().includes(searchTerm)) ||
        (product.barcode && product.barcode.toLowerCase().includes(searchTerm))
    );
    setFilteredProducts(filtered);
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

        <div className="card-body">
          <div className="mb-3">
            <div className="input-group">
              <span className="input-group-text">
                <i className="bi bi-search"></i>
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Buscar productos por nombre, descripción, categoría..."
                value={search}
                onChange={handleSearch}
              />
            </div>
          </div>

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