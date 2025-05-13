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
        }
      };
      fetchProduct();
    }
  }, [id]);



  const handleReset = () => {
    setFormData({
      name: '',
      description: '',
      location: '',
      stock: 0,
      category_id: '',
    });
    setStatus({ type: '', message: '' });
  };

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
    if (!formData.name || !formData.stock || !formData.category) {
      setStatus({ type: 'error', message: 'Nombre, Stock disponible y Categiria son campos requeridos' });
      setIsSubmitting(false);
      return;
    }
    // setError(null);
    try {
      if (id) {
        // Editar producto existente
        await api.put(`almacens/${id}/`, formData);
        showSuccessAlert("Producto actualizado correctamente.");
      } else {
        // Crear nuevo producto
        await api.post("/almacens/", formData);
        showSuccessAlert("Producto creado correctamente.");
      }
      handleReset()
      // navigate("/productsList"); // Redirige a la lista de productos
    } catch (err) {
      console.error("Error guardando producto:", err);
      showGenericAlert("No se pudo guardar el producto. Intenta nuevamente.");
    }
  };


  const handleCancel = () => {
    navigate('/');
  };
  

  return (
    <div className="container mt-5">
    {/* <div style={styles.formContainer}> */}
      <h2 style={styles.formHeader}>
        <span style={{ marginRight: '8px' }}><Package /></span>
        Agregar Artículo al Almacén
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
            <label style={styles.label} htmlFor="category">
              Categoría
            </label>
            <select
              id="category"
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
                <span style={{ marginRight: '8px' }}><Loader /></span>
                Guardando...
              </React.Fragment>
            ) : (
              <React.Fragment>
                <span style={{ marginRight: '8px' }}><Save /></span>
                Guardar Artículo
              </React.Fragment>
            )}
          </button>
        </div>
      </div>
    </div>
    // </div>
  );
};

export default AlmacenForm;