import React, { useState, useEffect } from 'react';
import { Save, Package, Check, AlertCircle, Tag, FileText, Loader } from 'lucide-react';
import { useNavigate, useParams} from "react-router-dom";
import {styles, showGenericAlert, showSuccessAlert} from "../herpert";
import api from "../services/api"; // Importa la instancia de Axios




const LabourForm = () => {
  const { id } = useParams();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: 0,
    factura_asociada: '',
  });

  const navigate = useNavigate();
  const [status, setStatus] = useState({ type: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hoverStates, setHoverStates] = useState({
    cancel: false,
    submit: false
  });



  // Cargar datos del producto si se está editando
  useEffect(() => {
    if (id) {
      const fetchProduct = async () => {
        try {
          const response = await api.get(`labours/${id}/`);
          setFormData(response.data); // Carga los datos en formData
        } catch (err) {
          console.error("Error cargando producto:");
        }
      };
      fetchProduct();
    }
  }, [id]);



  const handleReset = () => {
    setFormData({
        name: '',
        description: '',
        price: 0,
        factura_asociada: '',
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
      if (!formData.name || !formData.price) {
        setStatus({ type: 'error', message: 'Nombre y precio son campos requeridos' });
        setIsSubmitting(false);
        return;
      }
    
      try {
        let response;
        if (id) {
          response = await api.put(`labours/${id}/`, formData);
          showSuccessAlert("Servicio actualizado correctamente.");
        } else {
          response = await api.post("/labours/", formData);
          showSuccessAlert("El servicio fue creado correctamente.");
        }
        
        // Redirigir después de guardar
        setTimeout(() => navigate("/labour-list"), 1500);
      } catch (err) {
        console.error("Error al guardar:", err.response?.data);
        const errorMsg = err.response?.data?.detail || 
                       err.response?.data?.message || 
                       "Error al guardar el servicio";
        setStatus({ type: 'error', message: errorMsg });
      } finally {
        setIsSubmitting(false);
      }
    };


  const handleCancel = () => {
    navigate('/labour-list');
  };
  

  return (
    <div className="container mt-5">
    {/* <div style={styles.formContainer}> */}
      <h2 style={styles.formHeader}>
        <span style={{ marginRight: '8px' }}><Package /></span>
        Agregar Servicio Mano de Obra
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
              Nombre de la persona
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
                placeholder="Ingrese un nombre"
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
            <label style={styles.label} htmlFor="price">
              Precio del servicio
            </label>
            <input
              id="price"
              type="number"
              name="price"
              value={formData.price}
              onChange={handleChange}
              style={styles.input}
              min="0"
              required
              placeholder="0"
            />
          
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="factura_asociada">
              Factura asociada
            </label>
            <input
              id="factura_asociada"
              type="number"
              name="factura_asociada"
              value={formData.factura_asociada}
              onChange={handleChange}
              style={styles.input}
              min="0"
              required
              placeholder="0"
            />
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

export default LabourForm;