import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import { 
  FaUser, FaSave, FaArrowLeft, FaPlus, FaTrash, 
  FaEnvelope, FaPhone, FaMapMarkerAlt, FaIdCard, 
  FaStar, FaUserPlus, FaEdit, FaTimes, FaCheck,
  FaInfoCircle
} from 'react-icons/fa';

/* ─── CSS Moderno y Responsive (mismo diseño que los demás componentes) ─── */
const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap');

  .cf-root {
    --bg-page: #f8fafc;
    --surface: #ffffff;
    --surface-hover: #f1f5f9;
    --border: #e2e8f0;
    --border-dark: #cbd5e1;
    --text: #0f172a;
    --text-muted: #475569;
    --text-faint: #94a3b8;
    --primary: #3b82f6;
    --primary-dark: #2563eb;
    --primary-light: #eff6ff;
    --success: #10b981;
    --success-light: #d1fae5;
    --danger: #ef4444;
    --danger-light: #fee2e2;
    --warning: #f59e0b;
    --warning-light: #fed7aa;
    --purple: #8b5cf6;
    --purple-light: #ede9fe;
    --radius-sm: 0.5rem;
    --radius-md: 0.75rem;
    --radius-lg: 1rem;
    --shadow: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05);
    --font: 'Inter', system-ui, -apple-system, sans-serif;
    --mono: 'SF Mono', 'Monaco', monospace;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  .cf-root {
    font-family: var(--font);
    background: var(--bg-page);
    min-height: 100vh;
    color: var(--text);
  }

  /* Header */
  .cf-header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0.75rem 1rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    position: sticky;
    top: 0;
    z-index: 50;
    backdrop-filter: blur(8px);
    background: rgba(255,255,255,0.95);
  }

  @media (min-width: 768px) {
    .cf-header {
      padding: 0 1.5rem;
      height: 64px;
      flex-wrap: nowrap;
    }
  }

  .cf-header-title {
    font-size: 0.875rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
  }

  @media (min-width: 640px) {
    .cf-header-title {
      font-size: 1rem;
    }
  }

  /* Main Content */
  .cf-body {
    padding: 1rem;
    max-width: 900px;
    margin: 0 auto;
  }

  @media (min-width: 768px) {
    .cf-body {
      padding: 1.5rem;
    }
  }

  /* Card */
  .cf-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow);
    overflow: hidden;
    transition: box-shadow 0.2s ease;
  }

  .cf-card:hover {
    box-shadow: var(--shadow-md);
  }

  .cf-card-header {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
  }

  @media (min-width: 640px) {
    .cf-card-header {
      padding: 1.25rem 1.5rem;
    }
  }

  .cf-card-header h3 {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .cf-card-header p {
    font-size: 0.75rem;
    margin-top: 0.25rem;
    opacity: 0.8;
  }

  .cf-card-body {
    padding: 1.25rem;
  }

  @media (min-width: 640px) {
    .cf-card-body {
      padding: 1.75rem;
    }
  }

  /* Form */
  .cf-form-group {
    margin-bottom: 1.25rem;
  }

  .cf-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: var(--text);
  }

  .cf-label svg {
    color: var(--primary);
  }

  .cf-label .required {
    color: var(--danger);
    font-size: 0.75rem;
  }

  .cf-input,
  .cf-select,
  .cf-textarea {
    width: 100%;
    padding: 0.625rem 0.875rem;
    font-size: 0.875rem;
    border: 1.5px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface);
    transition: all 0.2s ease;
    font-family: var(--font);
  }

  .cf-input:focus,
  .cf-select:focus,
  .cf-textarea:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-light);
  }

  .cf-input.is-invalid,
  .cf-select.is-invalid,
  .cf-textarea.is-invalid {
    border-color: var(--danger);
  }

  .cf-input.is-invalid:focus,
  .cf-select.is-invalid:focus,
  .cf-textarea.is-invalid:focus {
    box-shadow: 0 0 0 3px var(--danger-light);
  }

  .cf-error {
    color: var(--danger);
    font-size: 0.6875rem;
    margin-top: 0.375rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .cf-hint {
    color: var(--text-faint);
    font-size: 0.6875rem;
    margin-top: 0.375rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  /* Grid Responsive */
  .cf-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  @media (min-width: 640px) {
    .cf-row {
      grid-template-columns: repeat(2, 1fr);
      gap: 1.25rem;
    }
  }

  /* Client Type Options */
  .cf-type-options {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.75rem;
    margin-top: 0.5rem;
  }

  @media (min-width: 640px) {
    .cf-type-options {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  .cf-type-option {
    border: 2px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;
    background: var(--surface);
    text-align: center;
  }

  .cf-type-option:hover {
    border-color: var(--primary);
    background: var(--primary-light);
    transform: translateY(-2px);
  }

  .cf-type-option.selected {
    border-color: var(--primary);
    background: var(--primary-light);
  }

  .cf-type-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    display: block;
  }

  .cf-type-label {
    font-weight: 600;
    font-size: 0.8125rem;
    margin-bottom: 0.25rem;
  }

  .cf-type-desc {
    font-size: 0.6875rem;
    color: var(--text-faint);
  }

  /* Action Buttons */
  .cf-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.75rem;
    padding-top: 1.5rem;
    margin-top: 0.5rem;
    border-top: 1px solid var(--border);
  }

  .cf-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 1.25rem;
    font-size: 0.8125rem;
    font-weight: 600;
    border-radius: var(--radius-sm);
    border: 1.5px solid transparent;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: var(--font);
    text-decoration: none;
  }

  .cf-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .cf-btn-primary {
    background: var(--primary);
    color: white;
  }

  .cf-btn-primary:hover:not(:disabled) {
    background: var(--primary-dark);
    transform: translateY(-1px);
  }

  .cf-btn-outline {
    border-color: var(--border);
    background: var(--surface);
    color: var(--text-muted);
  }

  .cf-btn-outline:hover:not(:disabled) {
    background: var(--surface-hover);
    border-color: var(--border-dark);
  }

  .cf-spinner {
    width: 0.875rem;
    height: 0.875rem;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Info Card */
  .cf-info-card {
    background: var(--primary-light);
    border: 1px solid var(--primary-light);
    border-radius: var(--radius-md);
    padding: 0.875rem 1rem;
    margin-top: 1rem;
  }

  .cf-info-card small {
    font-size: 0.75rem;
    color: var(--primary-dark);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  /* Loading State */
  .cf-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    gap: 1rem;
  }

  .cf-spinner-large {
    width: 2rem;
    height: 2rem;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
`;

function InjectStyles() {
  useEffect(() => {
    const id = "client-form-styles";
    if (!document.getElementById(id)) {
      const style = document.createElement("style");
      style.id = id;
      style.textContent = STYLES;
      document.head.appendChild(style);
    }
  }, []);
  return null;
}

/* ─── Componente Principal ─────────────────────────────────────────────── */
const ClientForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
    ruc_ci: '',
    client_type: 'occasional'
  });
  
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (id) {
      setIsEditMode(true);
      loadClient();
    }
  }, [id]);

  const loadClient = async () => {
    setLoading(true);
    try {
      const response = await api.get(`clients/${id}/`);
      setFormData({
        name: response.data.name || '',
        email: response.data.email || '',
        phone: response.data.phone || '',
        address: response.data.address || '',
        ruc_ci: response.data.ruc_ci || '',
        client_type: response.data.client_type || 'occasional'
      });
    } catch (error) {
      console.error('Error cargando cliente:', error);
      toast.error('Error al cargar los datos del cliente');
      navigate('/sales');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const handleTypeSelect = (type) => {
    setFormData(prev => ({ ...prev, client_type: type }));
    if (errors.client_type) {
      setErrors(prev => ({ ...prev, client_type: null }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'El nombre del cliente es requerido';
    } else if (formData.name.length < 2) {
      newErrors.name = 'El nombre debe tener al menos 2 caracteres';
    }
    
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Ingrese un email válido';
    }
    
    if (formData.ruc_ci && formData.ruc_ci.length < 5) {
      newErrors.ruc_ci = 'El RUC/CI debe tener al menos 5 caracteres';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      toast.error('Por favor corrija los errores del formulario');
      return;
    }
    
    setLoading(true);
    
    try {
      if (isEditMode) {
        await api.put(`clients/${id}/`, formData);
        toast.success('Cliente actualizado correctamente');
      } else {
        await api.post('clients/', formData);
        toast.success('Cliente creado correctamente');
      }
      
      if (!isEditMode) {
        const result = await Swal.fire({
          title: '¿Cliente creado!',
          text: '¿Deseas crear otro cliente?',
          icon: 'success',
          showCancelButton: true,
          confirmButtonText: 'Sí, crear otro',
          cancelButtonText: 'Volver al listado',
          confirmButtonColor: '#3b82f6',
          cancelButtonColor: '#6b7280'
        });
        
        if (result.isConfirmed) {
          setFormData({
            name: '',
            email: '',
            phone: '',
            address: '',
            ruc_ci: '',
            client_type: 'occasional'
          });
          setLoading(false);
          return;
        }
      }
      
      navigate('/sales');
    } catch (error) {
      console.error('Error guardando cliente:', error);
      if (error.response?.status === 400) {
        const backendErrors = error.response.data;
        const formattedErrors = {};
        Object.keys(backendErrors).forEach(key => {
          formattedErrors[key] = Array.isArray(backendErrors[key]) 
            ? backendErrors[key].join(', ') 
            : backendErrors[key];
        });
        setErrors(formattedErrors);
        toast.error('Error de validación. Revise los campos.');
      } else {
        toast.error('Error al guardar el cliente');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    const hasData = Object.values(formData).some(v => v && v.toString().trim());
    if (hasData) {
      Swal.fire({
        title: '¿Cancelar?',
        text: 'Los cambios no guardados se perderán',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        confirmButtonText: 'Sí, salir',
        cancelButtonText: 'Continuar editando'
      }).then((result) => {
        if (result.isConfirmed) {
          navigate('/clients');
        }
      });
    } else {
      navigate('/clients');
    }
  };

  const clientTypes = [
    { value: 'occasional', label: 'Ocasional', icon: '🔄', description: 'Cliente que compra esporádicamente' },
    { value: 'regular', label: 'Regular', icon: '📌', description: 'Cliente con compras frecuentes' },
    { value: 'frequent', label: 'Frecuente', icon: '⭐', description: 'Cliente VIP con volumen alto de compras' }
  ];

  if (loading && isEditMode) {
    return (
      <div className="cf-root">
        <InjectStyles />
        <div className="cf-loading">
          <div className="cf-spinner-large" />
          <span style={{ color: 'var(--text-muted)' }}>Cargando cliente...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="cf-root">
      <InjectStyles />
      <Toaster position="top-right" />

      {/* Header */}
      <header className="cf-header">
        <button className="cf-btn cf-btn-outline" onClick={() => navigate('/sales')}>
          <FaArrowLeft size={12} /> Volver
        </button>

        <div className="cf-header-title">
          {isEditMode ? <FaEdit size={14} /> : <FaUserPlus size={14} />}
          {isEditMode ? 'Editar Cliente' : 'Nuevo Cliente'}
        </div>
      </header>

      <div className="cf-body">
        <div className="cf-card">
          <div className="cf-card-header">
            <h3>
              {isEditMode ? <FaEdit size={20} /> : <FaUserPlus size={20} />}
              {isEditMode ? 'Editar Cliente' : 'Registrar Nuevo Cliente'}
            </h3>
            <p>
              {isEditMode 
                ? 'Actualice la información del cliente en el sistema' 
                : 'Complete los datos para registrar un nuevo cliente'}
            </p>
          </div>

          <div className="cf-card-body">
            <form onSubmit={handleSubmit}>
              {/* Nombre */}
              <div className="cf-form-group">
                <label className="cf-label">
                  <FaUser size={14} />
                  Nombre completo
                  <span className="required">*</span>
                </label>
                <input
                  type="text"
                  className={`cf-input ${errors.name ? 'is-invalid' : ''}`}
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Ej: Juan Pérez González"
                  disabled={loading}
                />
                {errors.name && (
                  <div className="cf-error">
                    <FaTimes size={10} /> {errors.name}
                  </div>
                )}
              </div>

              <div className="cf-row">
                {/* Email */}
                <div className="cf-form-group">
                  <label className="cf-label">
                    <FaEnvelope size={14} />
                    Correo electrónico
                  </label>
                  <input
                    type="email"
                    className={`cf-input ${errors.email ? 'is-invalid' : ''}`}
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="cliente@ejemplo.com"
                    disabled={loading}
                  />
                  {errors.email && (
                    <div className="cf-error">
                      <FaTimes size={10} /> {errors.email}
                    </div>
                  )}
                  <div className="cf-hint">
                    <FaInfoCircle size={10} /> Opcional pero recomendado
                  </div>
                </div>
                
                {/* Teléfono */}
                <div className="cf-form-group">
                  <label className="cf-label">
                    <FaPhone size={14} />
                    Teléfono
                  </label>
                  <input
                    type="tel"
                    className={`cf-input ${errors.phone ? 'is-invalid' : ''}`}
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder="0999 123 456"
                    disabled={loading}
                  />
                  {errors.phone && (
                    <div className="cf-error">
                      <FaTimes size={10} /> {errors.phone}
                    </div>
                  )}
                  <div className="cf-hint">
                    <FaInfoCircle size={10} /> Número de contacto
                  </div>
                </div>
              </div>

              <div className="cf-row">
                {/* RUC/CI */}
                <div className="cf-form-group">
                  <label className="cf-label">
                    <FaIdCard size={14} />
                    RUC / CI
                  </label>
                  <input
                    type="text"
                    className={`cf-input ${errors.ruc_ci ? 'is-invalid' : ''}`}
                    name="ruc_ci"
                    value={formData.ruc_ci}
                    onChange={handleChange}
                    placeholder="1712345678001"
                    disabled={loading}
                  />
                  {errors.ruc_ci && (
                    <div className="cf-error">
                      <FaTimes size={10} /> {errors.ruc_ci}
                    </div>
                  )}
                  <div className="cf-hint">
                    <FaInfoCircle size={10} /> Opcional para facturación
                  </div>
                </div>
                
                {/* Tipo de Cliente */}
                <div className="cf-form-group">
                  <label className="cf-label">
                    <FaStar size={14} />
                    Tipo de Cliente
                  </label>
                  <div className="cf-type-options">
                    {clientTypes.map(type => (
                      <div
                        key={type.value}
                        className={`cf-type-option ${formData.client_type === type.value ? 'selected' : ''}`}
                        onClick={() => handleTypeSelect(type.value)}
                      >
                        <span className="cf-type-icon">{type.icon}</span>
                        <div className="cf-type-label">{type.label}</div>
                        <div className="cf-type-desc">{type.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Dirección */}
              <div className="cf-form-group">
                <label className="cf-label">
                  <FaMapMarkerAlt size={14} />
                  Dirección
                </label>
                <textarea
                  className={`cf-textarea ${errors.address ? 'is-invalid' : ''}`}
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  rows="3"
                  placeholder="Dirección completa del cliente"
                  disabled={loading}
                />
                {errors.address && (
                  <div className="cf-error">
                    <FaTimes size={10} /> {errors.address}
                  </div>
                )}
              </div>

              {/* Botones */}
              <div className="cf-actions">
                <button
                  type="button"
                  className="cf-btn cf-btn-outline"
                  onClick={handleCancel}
                  disabled={loading}
                >
                  <FaArrowLeft size={12} /> Cancelar
                </button>
                <button
                  type="submit"
                  className="cf-btn cf-btn-primary"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <div className="cf-spinner" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <FaSave size={12} />
                      {isEditMode ? 'Actualizar Cliente' : 'Guardar Cliente'}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Información adicional */}
        <div className="cf-info-card">
          <small>
            <FaInfoCircle size={14} />
            <strong>Información:</strong> Los campos marcados con * son obligatorios.
            El cliente puede ser creado sin RUC/CI para ventas ocasionales.
            Los clientes frecuentes tendrán beneficios especiales.
          </small>
        </div>
      </div>
    </div>
  );
};

export default ClientForm;