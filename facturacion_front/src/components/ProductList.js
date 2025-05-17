import React, { useState, useEffect } from 'react';
import DataTable from 'react-data-table-component';
import api from '../services/api';
import { Link } from "react-router-dom";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import { useNavigate } from 'react-router-dom';
import {stylesAlmacens} from "../herpert";

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]); // Productos filtrados
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState(""); // Estado para búsqueda
  const navigate = useNavigate();

    const getStockStyle = (price) => {
      if (price <= 3) return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeLow };
      if (price <= 10) return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeMedium };
      return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeHigh };
    };

  useEffect(() => {
    const fetchProducts = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.get('products/');
        setProducts(response.data);
        setFilteredProducts(response.data); // Inicialmente, todos los productos
      } catch (error) {
        console.error('Error fetching products:', error);
        setError(error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, []);

  // Funciones para editar y eliminar productos
  const handleEdit = (id) => {
    navigate(`/productsForm/${id}`);
  };

    const handleDelete = async (id) => {
      const result = await showConfirmationAlert(
        "¿Estás seguro?",
        "Esta acción no se puede deshacer."
      );
    if (result.isConfirmed) {
      try {
        await api.delete(`/products/${id}/`);
        const updatedProduct = products.filter((produt) => produt.id !== id);
        setProducts(updatedProduct);
        setFilteredProducts(updatedProduct);
        showSuccessAlert("Eliminado", "El producto ha sido eliminado.");
        } catch (error) {
            showErrorAlert("Error", "No se pudo eliminar el producto.");
          }
        }
    };


    // Manejar la búsqueda
    const handleSearch = (event) => {
      const searchTerm = event.target.value.toLowerCase();
      setSearch(searchTerm);
      const filtered = products.filter(
        (product) =>
          product.name.toLowerCase().includes(searchTerm) ||
          product.description.toLowerCase().includes(searchTerm) ||
          (product.category_name && product.category_name.toLowerCase().includes(searchTerm))
      );
      setFilteredProducts(filtered);
    };

  // Configuración de las columnas de la tabla
  const columns = [
    {
      name: 'ID',
      selector: (row) => row.id,
      sortable: true,
    },
    {
      name: 'Nombre',
      selector: (row) => row.name,
      sortable: true,
    },

    {
      name: 'Descripción',
      selector: (row) => row.description,
      sortable: true,
      cell: (row) => (
        <div
          style={{
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: '200px',
            cursor: 'pointer',
          }}
          title={row.description} // Este es el tooltip que aparece al pasar el mouse
        >
          {row.description}
        </div>
      ),
    },
    
    {
      name: 'Categoría',
      selector: (row) => row.category_name || 'Sin categoría',
      sortable: true,
    },
    {
      name: 'Precio',
      cell: (row) => `$${parseFloat(row.price).toFixed(2)}`,
      sortable: true,
    },
    {
      name: 'Stock',
      sortable: true,
      cell: (row) => (
        <span style={getStockStyle(row.stock)}>
          {row.stock}
        </span>
      ),
    },
    
    
    {
      name: 'Acciones',
      cell: (row) => (
        <div>
          <button
            className="btn btn-primary btn-sm me-2"
            onClick={() => handleEdit(row.id)}
          >
            Editar
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => handleDelete(row.id)}
          >
            Eliminar
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="container mt-5">
      <h1 className="mb-4">Lista de Productos</h1>

      {/* Input de búsqueda */}
      <div className="mb-3 d-flex">
        <input
          type="text"
          className="form-control me-2"
          placeholder="Buscar productos..."
          value={search}
          onChange={handleSearch}
        />
        <button className="btn btn-primary" onClick={() => handleSearch({ target: { value: search } })}>
          Buscar
        </button>
      </div>

      {isLoading && <p>Cargando productos...</p>}
      {error && <p className="text-danger">Error: {error.message}</p>}
      {!isLoading && (
        <DataTable
          title="Productos"
          columns={columns}
          data={filteredProducts} // Usar productos filtrados
          pagination
          highlightOnHover
          striped
          responsive
          noDataComponent={<p>No se encontraron productos.</p>}
        />
      )}
      <Link to="/productsForm" className="btn btn-primary m-2">Crear Productos</Link>
      <Link to="/" className="btn btn-danger m-2">Cancelar</Link>
    </div>
  );
};

export default ProductList;
