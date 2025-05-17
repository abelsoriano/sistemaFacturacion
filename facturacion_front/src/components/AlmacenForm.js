import React, { useState, useEffect } from 'react';
import { Save, Package, Check, AlertCircle, Tag, MapPin, FileText, Loader } from 'lucide-react';
import { useNavigate, useParams} from "react-router-dom";
import {styles, showGenericAlert, showSuccessAlert} from "../herpert";
import api from "../services/api"; // Importa la instancia de Axios

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
  const [hoverStates, setHoverStates] = useState({
    cancel: false,
    submit: false
  });

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

      console.log("Datos a enviar:", dataToSend); // Para depuración
      
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
    <div className="container mt-5">
      <h2 style={styles.formHeader}>
        <span style={{ marginRight: '8px' }}><Package /></span>
        {id ? 'Editar Artículo' : 'Agregar Artículo al Almacén'}
      </h2>

      {status.message && (
        <div style={{
          ...styles.alertBox,
          ...(status.type === 'success' ? styles.successAlert : styles.errorAlert)
        }}>
          <span style={styles.icon}>
            {status.type === 'success' ? <Check /> : <AlertCircle />}
          </span>
          <span>{status.message}</span>
        </div>
      )}

      <div>
        <div style={styles.formGrid}>
          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="name">
              Nombre del artículo
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="name"
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                style={{
                  ...styles.input,
                  paddingLeft: '36px'
                }}
                placeholder="Ej: Monitor LCD 24"
                required
              />
              <div style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#9ca3af'
              }}>
                <Tag />
              </div>
            </div>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="location">
              Ubicación
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="location"
                type="text"
                name="location"
                value={formData.location}
                onChange={handleChange}
                style={{
                  ...styles.input,
                  paddingLeft: '36px'
                }}
                placeholder="Ej: Estante A, Bodega 2"
              />
              <div style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#9ca3af'
              }}>
                <MapPin />
              </div>
            </div>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="stock">
              Stock disponible
            </label>
            <input
              id="stock"
              type="number"
              name="stock"
              value={formData.stock}
              onChange={handleChange}
              style={styles.input}
              min="0"
              required
              placeholder="0"
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="category_id">
              Categoría
            </label>
            <select
              id="category_id"
              name="category_id"
              value={formData.category_id}
              onChange={handleChange}
              style={styles.select}
              required
            >
              <option value="">Seleccionar categoría</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label} htmlFor="description">
            Descripción
          </label>
          <div style={{ position: 'relative' }}>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              style={{
                ...styles.textarea,
                paddingLeft: '36px'
              }}
              placeholder="Ingresa los detalles relevantes del artículo..."
            />
            <div style={{
              position: 'absolute',
              left: '12px',
              top: '16px',
              color: '#9ca3af'
            }}>
              <FileText />
            </div>
          </div>
        </div>

        <div style={styles.buttonContainer}>
          <button
            type="button"
            onClick={handleCancel}
            onMouseEnter={() => setHoverStates(prev => ({ ...prev, cancel: true }))}
            onMouseLeave={() => setHoverStates(prev => ({ ...prev, cancel: false }))}
            style={{
              ...styles.button,
              ...styles.cancelButton,
              ...(hoverStates.cancel ? styles.cancelButtonHover : {})
            }}
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleSubmit}
            onMouseEnter={() => setHoverStates(prev => ({ ...prev, submit: true }))}
            onMouseLeave={() => setHoverStates(prev => ({ ...prev, submit: false }))}
            style={{
              ...styles.button,
              ...styles.submitButton,
              ...(hoverStates.submit && !isSubmitting ? styles.submitButtonHover : {}),
              ...(isSubmitting ? styles.submitButtonDisabled : {})
            }}
          >
            {isSubmitting ? (
              <React.Fragment>
                <span style={{ marginRight: '8px', display: 'inline-block', animation: 'spin 1s linear infinite' }}><Loader /></span>
                Guardando...
              </React.Fragment>
            ) : (
              <React.Fragment>
                <span style={{ marginRight: '8px' }}><Save /></span>
                {id ? 'Actualizar Artículo' : 'Guardar Artículo'}
              </React.Fragment>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AlmacenForm;