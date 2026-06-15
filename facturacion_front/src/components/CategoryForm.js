import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from "react-router-dom";
import api from '../services/api';
import { showGenericAlert, showSuccessAlert } from "../herpert";
import { FaFolder, FaSave } from 'react-icons/fa';
import '../css/Category.css';

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
    <div className="cat-form-shell">
      <div className="cat-form-wrap">
        <div className="cat-form-header">
          <span className="cat-form-header-icon"><FaFolder size={18} /></span>
          <div>
            <h1>{id ? 'Editar categoría' : 'Agregar categoría'}</h1>
            <p>Organiza inventario y productos sin cambiar reglas operativas.</p>
          </div>
        </div>

        <form className="cat-form-card" onSubmit={handleSubmit}>
          <div className="cat-form-group">
            <label htmlFor="category-name">Nombre de la categoría</label>
            <input
              id="category-name"
              type="text"
              className="cat-form-input"
              placeholder="Ej: Repuestos, Servicios, Accesorios"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          {error && <p className="cat-form-error">{error}</p>}
          <div className="cat-form-actions">
            <Link to="/categoriaList" className="cat-form-button secondary">Cancelar</Link>
            <button type="submit" className="cat-form-button primary">
              <FaSave size={14} />
              {id ? 'Actualizar' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CategoryForm;
