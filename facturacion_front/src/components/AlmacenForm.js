import React, { useState, useEffect } from 'react';
import { Save, Package, Check, AlertCircle, Tag, MapPin, FileText, Loader } from 'lucide-react';
import { useNavigate, useParams} from "react-router-dom";
import {showGenericAlert, showSuccessAlert} from "../herpert";
import api from "../services/api"; // Importa la instancia de Axios
import '../css/AlmacenList.css';

const AlmacenForm = () => {
  const { id } = useParams();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    location: '',
    stock: 0,
    category_id: '',
  });

  const navigate = useNavigate();

  const [categories, setCategories] = useState([]);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await api.get("categories/");
        setCategories(response.data);
      } catch (err) {
        showGenericAlert("Error al obtener las categorías.");
        console.error("Error al obtener categorías:", err);
      }
    };

    fetchCategories();
  }, []);

  // Cargar datos del producto si se está editando
  useEffect(() => {
    if (id) {
      const fetchProduct = async () => {
        try {
          const response = await api.get(`almacens/${id}/`);
          setFormData(response.data); // Carga los datos en formData
        } catch (err) {
          console.error("Error cargando producto:", err);
          showGenericAlert("Error al cargar los datos del producto.");
        }
      };
      fetchProduct();
    }
  }, [id]);


  // Manejar cambios en los campos del formulario
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatus({ type: '', message: '' });

    // Validación básica
    if (!formData.name || formData.stock === '' || !formData.category_id) {
      setStatus({ 
        type: 'error', 
        message: 'Nombre, Stock disponible y Categoría son campos requeridos' 
      });
      setIsSubmitting(false);
      return;
    }

    try {
      // Creamos una copia del formData para enviar al servidor
      const dataToSend = {
        ...formData,
        stock: parseInt(formData.stock, 10) // Asegurarse que stock es un número
      };

      // console.log("Datos a enviar:", dataToSend); // Para depuración
      
      if (id) {
        // Editar producto existente
        await api.put(`almacens/${id}/`, dataToSend);
        showSuccessAlert("Producto actualizado correctamente.");
        navigate("/list-item"); // Redirige a la lista de productos
      } else {
        // Crear nuevo producto
        await api.post("/almacens/", dataToSend);
        showSuccessAlert("Producto creado correctamente.");
        navigate("/list-item"); // Redirige a la lista de productos
      }
    } catch (err) {
      console.error("Error guardando producto:", err);
      
      // Mostrar mensaje de error más específico si está disponible
      if (err.response && err.response.data) {
        const errorMsg = typeof err.response.data === 'string' 
          ? err.response.data 
          : JSON.stringify(err.response.data);
        setStatus({
          type: 'error',
          message: `Error: ${errorMsg}`
        });
      } else {
        showGenericAlert("No se pudo guardar el producto. Intenta nuevamente.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    navigate('/list-item');
  };
  
  return (
    <div className="alm-form-shell">
      <div className="alm-form-wrap">
        <div className="alm-form-header">
          <span className="alm-form-header-icon"><Package size={22} /></span>
          <div>
            <h1>{id ? 'Editar artículo' : 'Agregar artículo al almacén'}</h1>
            <p>Registra artículos operativos sin modificar la lógica de inventario.</p>
          </div>
        </div>

        {status.message && (
          <div className={`alm-alert ${status.type === 'success' ? 'success' : 'error'}`}>
            {status.type === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}
            <span>{status.message}</span>
          </div>
        )}

        <form className="alm-form-card" onSubmit={handleSubmit}>
          <div className="alm-form-grid">
            <div className="alm-form-group">
              <label htmlFor="name">Nombre del artículo</label>
              <div className="alm-input-shell">
                <Tag size={17} />
                <input
                  id="name"
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="alm-form-input"
                  placeholder="Ej: Monitor LCD 24"
                  required
                />
              </div>
            </div>

            <div className="alm-form-group">
              <label htmlFor="location">Ubicación</label>
              <div className="alm-input-shell">
                <MapPin size={17} />
                <input
                  id="location"
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  className="alm-form-input"
                  placeholder="Ej: Estante A, Bodega 2"
                />
              </div>
            </div>

            <div className="alm-form-group">
              <label htmlFor="stock">Stock disponible</label>
              <input
                id="stock"
                type="number"
                name="stock"
                value={formData.stock}
                onChange={handleChange}
                className="alm-form-input"
                min="0"
                required
                placeholder="0"
              />
            </div>

            <div className="alm-form-group">
              <label htmlFor="category_id">Categoría</label>
              <select
                id="category_id"
                name="category_id"
                value={formData.category_id}
                onChange={handleChange}
                className="alm-form-select"
                required
              >
                <option value="">Seleccionar categoría</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
            </div>

            <div className="alm-form-group alm-form-full">
              <label htmlFor="description">Descripción</label>
              <div className="alm-input-shell alm-textarea-shell">
                <FileText size={17} />
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  className="alm-form-textarea"
                  placeholder="Ingresa los detalles relevantes del artículo..."
                />
              </div>
            </div>
          </div>

          <div className="alm-form-actions">
            <button type="button" onClick={handleCancel} className="btn-secondary">
              Cancelar
            </button>
            <button type="submit" disabled={isSubmitting} className="btn-primary">
              {isSubmitting ? (
                <React.Fragment>
                  <Loader size={17} />
                  Guardando...
                </React.Fragment>
              ) : (
                <React.Fragment>
                  <Save size={17} />
                  {id ? 'Actualizar artículo' : 'Guardar artículo'}
                </React.Fragment>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AlmacenForm;
