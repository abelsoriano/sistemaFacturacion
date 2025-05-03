import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from "react-router-dom";
import api from '../services/api';
import { showGenericAlert, showSuccessAlert } from "../herpert";

function CategoryForm() {
  const [name, setName] = useState('');
  const [error, setError] = useState(null);
  const { id } = useParams(); // Obtén el id de la URL
  const navigate = useNavigate();

  // Cargar datos si se está editando
  useEffect(() => {
    if (id) {
      const fetchCategory = async () => {
        try {
          const response = await api.get(`categories/${id}/`);
          setName(response.data.name);
        } catch (err) {
          console.error('Error cargando categoría:', err);
          setError('No se pudo cargar la categoría.');
        }
      };
      fetchCategory();
    }
  }, [id]);

  const handleSubmit = async (e) => {
    e.preventDefault(); // Evita el envío predeterminado del formulario
    setError(null);
    try {
      if (id) {
        // Editar categoría existente
        await api.put(`categories/${id}/`, { name });
        showSuccessAlert('Categoría actualizada correctamente.');
      } else {
        // Crear nueva categoría
        await api.post('categories/', { name });
        showSuccessAlert('Categoría creada correctamente.');
      }
      navigate('/categoriaList'); // Redirige a la lista de categorías
    } catch (err) {
      console.error('Error guardando categoría:', err);
      showGenericAlert('No se pudo guardar la categoría. Intenta nuevamente.');
    }
  };

  return (
    <div className="container mt-5">
      <h2 className="text-center mb-4">{id ? 'Editar Categoría' : 'Agregar Categoría'}</h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label">Nombre de la Categoría</label>
          <input 
            type="text" 
            className="form-control" 
            placeholder="Ingrese el nombre" 
            value={name} 
            onChange={(e) => setName(e.target.value)} 
            required 
          />
        </div>
        {error && <p className="text-danger">{error}</p>}
        <button type="submit" className="btn btn-primary">{id ? 'Actualizar' : 'Guardar'}</button>
        <Link to="/categoriaList" className="btn btn-danger m-2">Cancelar</Link>
      </form>
    </div>
  );
}

export default CategoryForm;
