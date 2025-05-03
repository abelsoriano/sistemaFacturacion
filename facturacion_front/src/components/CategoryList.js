import React, { useState, useEffect } from "react";
import DataTable from "react-data-table-component";
import api from "../services/api";
import { Link } from "react-router-dom";
import { useNavigate } from 'react-router-dom';

import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";

const CategoryList = () => {
    const [categories, setCateories] = useState([]);
    const [filteredCategory, setFilteredCategory] = useState([]); // Productos filtrados
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState(""); // Estado para búsqueda
    const navigate = useNavigate();

  
    useEffect(() => {
      const fetchCategoria = async () => {
        setIsLoading(true);
        setError(null);
        try {
          const response = await api.get('categories/');
          if (response.data.length === 0) {
            console.log('No products found');
          } else {
            setCateories(response.data);
            setFilteredCategory(response.data); // Inicialmente, todos los productos
          }
        } catch (error) {
          console.error('Error fetching products:', error);
          setError(error);
        } finally {
          setIsLoading(false);
        }
      };
  
      fetchCategoria();
    }, []);

      // Funciones para editar y eliminar productos
    const handleEdit = (id) => {
        navigate(`/categoriesForm/${id}`);
    };

  const handleDelete = async (id) => {
    const result = await showConfirmationAlert(
      "¿Estás seguro?",
      "Esta acción no se puede deshacer."
    );
  if (result.isConfirmed) {
    try {
      await api.delete(`/categories/${id}/`);
      const updatedCategories = categories.filter((categori) => categori.id !== id);
      setCateories(updatedCategories);
      setFilteredCategory(updatedCategories);
      showSuccessAlert("Eliminado", "La categoria ha sido eliminado.");
      } catch (error) {
          showErrorAlert("Error", "No se pudo eliminar el categoria.");
        }
      }
  };

  // Manejar la búsqueda
  const handleSearch = (event) => {
    const searchTerm = event.target.value.toLowerCase();
    setSearch(searchTerm);
    const filtered = categories.filter(
      (categoria) =>
        categoria.name.toLowerCase().includes(searchTerm)
    );
    setFilteredCategory(filtered);
  };

  // Configuración de las columnas de la tabla
  const columns = [
    {
      name: "ID",
      selector: (row) => row.id,
      sortable: true,
    },
    {
      name: "Nombre",
      selector: (row) => row.name,
      sortable: true,
    },

    {
      name: "Acciones",
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
    <h1 className="mb-4">Lista de Categoria</h1>

    {/* Input de búsqueda */}
    <div className="mb-3 d-flex">
        <input
          type="text"
          className="form-control me-2"
          placeholder="Buscar categoria..."
          value={search}
          onChange={handleSearch}
        />
        <button className="btn btn-primary" onClick={() => handleSearch({ target: { value: search } })}>
          Buscar
        </button>
      </div>


    {isLoading && <p>Cargando categoria...</p>}
    {error && <p className="text-danger">Error: {error.message}</p>}
    {!isLoading && (
      <DataTable
        title="Categorias"
        columns={columns}
        data={filteredCategory} // Usar productos filtrados
        pagination
        highlightOnHover
        striped
        responsive
        noDataComponent={<p>No se encontraron productos.</p>}
      />
    )}
    <Link to="/categoriesForm" className="btn btn-primary m-2"> Crear Productos</Link>
    <Link to="/" className="btn btn-danger m-2"> Cancelar</Link>
    
  </div>
  );
};

export default CategoryList;
