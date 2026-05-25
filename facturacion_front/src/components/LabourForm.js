import React, { useState, useEffect } from 'react';
import { Save, Package, Check, AlertCircle, Tag, FileText, Loader, CreditCard, DollarSign } from 'lucide-react';
import { useNavigate, useParams } from "react-router-dom";
import { styles, showSuccessAlert } from "../herpert";
import api from "../services/api";

const ServicioForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    nombre_persona: '',
    descripcion: '',
    precio_total: '',
    factura_asociada: '',
    modalidad_pago: 'contado',
  });

  const [status, setStatus] = useState({ type: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hoverStates, setHoverStates] = useState({ cancel: false, submit: false });

  // Cargar datos si se está editando
  useEffect(() => {
    if (id) {
      const fetchServicio = async () => {
        try {
          const response = await api.get(`servicios-mano-obra/${id}/`);
          setFormData({
            nombre_persona: response.data.nombre_persona || '',
            descripcion: response.data.descripcion || '',
            precio_total: response.data.precio_total || '',
            factura_asociada: response.data.factura_asociada || '',
            modalidad_pago: response.data.modalidad_pago || 'contado',
          });
        } catch (err) {
          console.error("Error cargando servicio:", err);
          setStatus({ type: 'error', message: 'Error al cargar los datos del servicio.' });
        }
      };
      fetchServicio();
    }
  }, [id]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatus({ type: '', message: '' });

    // Validaciones
    const errors = [];
    if (!formData.nombre_persona.trim()) errors.push('El nombre de la persona es requerido');
    if (!formData.precio_total || isNaN(parseFloat(formData.precio_total)) || parseFloat(formData.precio_total) <= 0) {
      errors.push('El precio debe ser un número mayor que cero');
    }

    if (errors.length > 0) {
      setStatus({ type: 'error', message: errors.join('. ') });
      setIsSubmitting(false);
      return;
    }

    try {
      const dataToSend = {
        ...formData,
        precio_total: parseFloat(formData.precio_total),
        factura_asociada: formData.factura_asociada || null,
      };

      if (id) {
        await api.put(`servicios-mano-obra/${id}/`, dataToSend);
        showSuccessAlert("Servicio actualizado correctamente.");
      } else {
        await api.post("servicios-mano-obra/", dataToSend);
        showSuccessAlert("Servicio creado correctamente.");
      }

      setTimeout(() => navigate("/labour-list"), 1500);
    } catch (err) {
      console.error("Error al guardar:", err);
      let errorMsg = "Error al guardar el servicio. Intente nuevamente.";

      if (err.response?.data && typeof err.response.data === 'object') {
        const details = Object.entries(err.response.data).map(([field, errs]) =>
          `${field}: ${Array.isArray(errs) ? errs.join(', ') : errs}`
        );
        if (details.length > 0) errorMsg = details.join('. ');
      } else if (typeof err.response?.data === 'string') {
        errorMsg = err.response.data;
      }

      setStatus({ type: 'error', message: errorMsg });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mt-5">
      <h2 style={styles.formHeader}>
        <span style={{ marginRight: '8px' }}><Package /></span>
        {id ? 'Editar Servicio de Mano de Obra' : 'Nuevo Servicio de Mano de Obra'}
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

          {/* Nombre */}
          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="nombre_persona">
              Nombre de la persona
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="nombre_persona"
                type="text"
                name="nombre_persona"
                value={formData.nombre_persona}
                onChange={handleChange}
                style={{ ...styles.input, paddingLeft: '36px' }}
                placeholder="Ingrese el nombre"
                required
              />
              <div style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }}>
                <Tag />
              </div>
            </div>
          </div>

          {/* Precio */}
          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="precio_total">
              Precio del servicio
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="precio_total"
                type="number"
                name="precio_total"
                value={formData.precio_total}
                onChange={handleChange}
                style={{ ...styles.input, paddingLeft: '36px' }}
                min="0"
                step="0.01"
                placeholder="0.00"
                required
              />
              <div style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }}>
                <DollarSign size={16} />
              </div>
            </div>
          </div>

          {/* Factura */}
          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="factura_asociada">
              Factura asociada
            </label>
            <input
              id="factura_asociada"
              type="text"
              name="factura_asociada"
              value={formData.factura_asociada}
              onChange={handleChange}
              style={styles.input}
              placeholder="Número de factura (opcional)"
            />
          </div>

          {/* Modalidad de pago */}
          <div style={styles.formGroup}>
            <label style={styles.label} htmlFor="modalidad_pago">
              Modalidad de pago
            </label>
            <div style={{ position: 'relative' }}>
              <select
                id="modalidad_pago"
                name="modalidad_pago"
                value={formData.modalidad_pago}
                onChange={handleChange}
                style={{ ...styles.input, paddingLeft: '36px', appearance: 'none', cursor: 'pointer' }}
              >
                <option value="contado">Contado (pago inmediato)</option>
                <option value="credito">Crédito (abonos)</option>
              </select>
              <div style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }}>
                <CreditCard size={16} />
              </div>
            </div>
          </div>

        </div>

        {/* Indicador visual si es crédito */}
        {formData.modalidad_pago === 'credito' && (
          <div style={{
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '8px',
            padding: '12px 16px',
            marginBottom: '16px',
            color: '#1d4ed8',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <CreditCard size={16} />
            <span>
              Este servicio se registrará a crédito. Podrás registrar abonos desde la lista de servicios una vez guardado.
            </span>
          </div>
        )}

        {/* Descripción */}
        <div style={styles.formGroup}>
          <label style={styles.label} htmlFor="descripcion">
            Descripción
          </label>
          <div style={{ position: 'relative' }}>
            <textarea
              id="descripcion"
              name="descripcion"
              value={formData.descripcion}
              onChange={handleChange}
              style={{ ...styles.textarea, paddingLeft: '36px' }}
              placeholder="Ingresa los detalles del servicio..."
            />
            <div style={{ position: 'absolute', left: '12px', top: '16px', color: '#9ca3af' }}>
              <FileText />
            </div>
          </div>
        </div>

        {/* Botones */}
        <div style={styles.buttonContainer}>
          <button
            type="button"
            onClick={() => navigate('/labour-list')}
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
                Guardar Servicio
              </React.Fragment>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ServicioForm;