import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import { showSuccessAlert, showGenericAlert } from '../herpert';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import { 
  FaArrowLeft, FaSave, FaPlus, FaEdit, FaTimes,
  FaBarcode, FaTag, FaFolderOpen, FaMapMarkerAlt,
  FaBuilding, FaFileAlt, FaCog, FaChartLine,
  FaMoneyBillWave, FaCalendarAlt, FaShieldAlt,
  FaWrench, FaClipboardList, FaUser, FaBox,
  FaInfoCircle, FaCheck, FaExclamationTriangle
} from 'react-icons/fa';

/* ─── CSS Moderno y Responsive ──────────────────────────────────────────── */
const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap');

  .af-root {
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
    --info: #06b6d4;
    --info-light: #cffafe;
    --radius-sm: 0.5rem;
    --radius-md: 0.75rem;
    --radius-lg: 1rem;
    --shadow: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05);
    --font: 'Inter', system-ui, -apple-system, sans-serif;
    --mono: 'SF Mono', 'Monaco', monospace;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  .af-root {
    font-family: var(--font);
    background: var(--bg-page);
    min-height: 100vh;
    color: var(--text);
  }

  /* Header */
  .af-header {
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
    .af-header {
      padding: 0 1.5rem;
      height: 64px;
      flex-wrap: nowrap;
    }
  }

  .af-header-title {
    font-size: 0.875rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
  }

  @media (min-width: 640px) {
    .af-header-title {
      font-size: 1rem;
    }
  }

  /* Main Content */
  .af-body {
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  @media (min-width: 768px) {
    .af-body {
      padding: 1.5rem;
    }
  }

  /* Card */
  .af-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow);
    overflow: hidden;
    transition: box-shadow 0.2s ease;
  }

  .af-card:hover {
    box-shadow: var(--shadow-md);
  }

  .af-card-header {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
  }

  @media (min-width: 640px) {
    .af-card-header {
      padding: 1.25rem 1.5rem;
    }
  }

  .af-card-header h4 {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .af-card-body {
    padding: 1.25rem;
  }

  @media (min-width: 640px) {
    .af-card-body {
      padding: 1.75rem;
    }
  }

  /* Section */
  .af-section {
    margin-bottom: 2rem;
  }

  .af-section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text);
    border-bottom: 2px solid var(--border);
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
  }

  .af-section-title svg {
    color: var(--primary);
  }

  /* Form Grid */
  .af-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  @media (min-width: 640px) {
    .af-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 1.25rem;
    }
  }

  @media (min-width: 1024px) {
    .af-grid {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  .af-full-width {
    grid-column: 1 / -1;
  }

  /* Form Group */
  .af-form-group {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .af-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text);
  }

  .af-label svg {
    color: var(--primary);
    font-size: 0.75rem;
  }

  .af-label .required {
    color: var(--danger);
    font-size: 0.6875rem;
  }

  .af-input,
  .af-select,
  .af-textarea {
    width: 100%;
    padding: 0.625rem 0.875rem;
    font-size: 0.875rem;
    border: 1.5px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface);
    transition: all 0.2s ease;
    font-family: var(--font);
  }

  .af-input:focus,
  .af-select:focus,
  .af-textarea:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-light);
  }

  .af-input:disabled,
  .af-select:disabled,
  .af-textarea:disabled {
    background: var(--surface-hover);
    cursor: not-allowed;
  }

  .af-hint {
    font-size: 0.6875rem;
    color: var(--text-faint);
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  /* Status Badges */
  .af-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .status-available {
    background: var(--success-light);
    color: var(--success);
  }
  .status-in_use {
    background: var(--primary-light);
    color: var(--primary);
  }
  .status-maintenance {
    background: var(--warning-light);
    color: var(--warning);
  }
  .status-damaged {
    background: var(--danger-light);
    color: var(--danger);
  }
  .status-retired {
    background: var(--surface-hover);
    color: var(--text-muted);
  }

  /* Condition Badges */
  .condition-excellent {
    background: var(--success-light);
    color: var(--success);
  }
  .condition-good {
    background: var(--primary-light);
    color: var(--primary);
  }
  .condition-fair {
    background: var(--warning-light);
    color: var(--warning);
  }
  .condition-poor {
    background: var(--danger-light);
    color: var(--danger);
  }

  /* Action Buttons */
  .af-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.75rem;
    padding-top: 1.5rem;
    margin-top: 1rem;
    border-top: 1px solid var(--border);
  }

  .af-btn {
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

  .af-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .af-btn-primary {
    background: var(--primary);
    color: white;
  }

  .af-btn-primary:hover:not(:disabled) {
    background: var(--primary-dark);
    transform: translateY(-1px);
  }

  .af-btn-secondary {
    border-color: var(--border);
    background: var(--surface);
    color: var(--text-muted);
  }

  .af-btn-secondary:hover:not(:disabled) {
    background: var(--surface-hover);
    border-color: var(--border-dark);
  }

  .af-spinner {
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

  /* Loading State */
  .af-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    gap: 1rem;
  }

  .af-spinner-large {
    width: 2.5rem;
    height: 2.5rem;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  /* Badge */
  .af-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.625rem;
    border-radius: 9999px;
    font-size: 0.6875rem;
    font-weight: 500;
    background: var(--surface-hover);
    color: var(--text-muted);
  }
`;

function InjectStyles() {
  useEffect(() => {
    const id = "asset-form-styles";
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
function AssetForm() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditMode = Boolean(id);

  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    category: '',
    brand: '',
    model: '',
    serial_number: '',
    status: 'available',
    condition: 'good',
    location: '',
    assigned_to: '',
    purchase_price: '',
    purchase_date: '',
    warranty_expiry: '',
    last_maintenance: '',
    next_maintenance: '',
    maintenance_notes: '',
    notes: ''
  });

  const STATUS_CHOICES = [
    { value: 'available', label: 'Disponible', icon: '✅' },
    { value: 'in_use', label: 'En Uso', icon: '👤' },
    { value: 'maintenance', label: 'En Mantenimiento', icon: '🔧' },
    { value: 'damaged', label: 'Dañado', icon: '⚠️' },
    { value: 'retired', label: 'Dado de Baja', icon: '📦' }
  ];

  const CONDITION_CHOICES = [
    { value: 'excellent', label: 'Excelente', icon: '🌟' },
    { value: 'good', label: 'Bueno', icon: '👍' },
    { value: 'fair', label: 'Regular', icon: '👌' },
    { value: 'poor', label: 'Malo', icon: '👎' }
  ];

  useEffect(() => {
    fetchCategories();
    if (isEditMode) {
      fetchAsset();
    }
  }, [id]);

  const fetchCategories = async () => {
    try {
      const response = await api.get('assets/categories/');
      setCategories(response.data);
    } catch (error) {
      console.error('Error al cargar categorías:', error);
      toast.error('Error al cargar las categorías');
    }
  };

  const fetchAsset = async () => {
    try {
      setLoading(true);
      const response = await api.get(`assets/${id}/`);
      setFormData({
        code: response.data.code || '',
        name: response.data.name || '',
        description: response.data.description || '',
        category: response.data.category?.id || '',
        brand: response.data.brand || '',
        model: response.data.model || '',
        serial_number: response.data.serial_number || '',
        status: response.data.status || 'available',
        condition: response.data.condition || 'good',
        location: response.data.location || '',
        assigned_to: response.data.assigned_to || '',
        purchase_price: response.data.purchase_price || '',
        purchase_date: response.data.purchase_date || '',
        warranty_expiry: response.data.warranty_expiry || '',
        last_maintenance: response.data.last_maintenance || '',
        next_maintenance: response.data.next_maintenance || '',
        maintenance_notes: response.data.maintenance_notes || '',
        notes: response.data.notes || ''
      });
    } catch (error) {
      console.error('Error al cargar activo:', error);
      toast.error('Error al cargar el activo');
      navigate('/assets');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateForm = () => {
    if (!formData.code.trim()) {
      toast.error('El código es obligatorio');
      return false;
    }
    if (!formData.name.trim()) {
      toast.error('El nombre es obligatorio');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);

      const dataToSend = {
        ...formData,
        category: formData.category || null,
        purchase_price: formData.purchase_price || null,
        purchase_date: formData.purchase_date || null,
        warranty_expiry: formData.warranty_expiry || null,
        last_maintenance: formData.last_maintenance || null,
        next_maintenance: formData.next_maintenance || null
      };

      if (isEditMode) {
        await api.put(`assets/${id}/`, dataToSend);
        toast.success('Activo actualizado exitosamente');
      } else {
        await api.post('assets/', dataToSend);
        toast.success('Activo registrado exitosamente');
        
        // Preguntar si quiere crear otro
        const result = await Swal.fire({
          title: '¿Activo creado!',
          text: '¿Deseas crear otro activo?',
          icon: 'success',
          showCancelButton: true,
          confirmButtonText: 'Sí, crear otro',
          cancelButtonText: 'Volver al listado',
          confirmButtonColor: '#3b82f6',
          cancelButtonColor: '#6b7280'
        });
        
        if (result.isConfirmed) {
          setFormData({
            code: '',
            name: '',
            description: '',
            category: '',
            brand: '',
            model: '',
            serial_number: '',
            status: 'available',
            condition: 'good',
            location: '',
            assigned_to: '',
            purchase_price: '',
            purchase_date: '',
            warranty_expiry: '',
            last_maintenance: '',
            next_maintenance: '',
            maintenance_notes: '',
            notes: ''
          });
          setLoading(false);
          return;
        }
      }

      navigate('/assetsManager');
    } catch (error) {
      console.error('Error al guardar activo:', error);
      if (error.response?.data) {
        const errorMsg = Object.entries(error.response.data)
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
        toast.error(errorMsg || 'Error al guardar el activo');
      } else {
        toast.error('Error al guardar el activo');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    const hasData = Object.values(formData).some(v => v && v.toString().trim());
    if (hasData && !isEditMode) {
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
          navigate('/assetsManager');
        }
      });
    } else {
      navigate('/assetsManager');
    }
  };

  const getStatusBadgeClass = (status) => {
    return `status-${status}`;
  };

  const getConditionBadgeClass = (condition) => {
    return `condition-${condition}`;
  };

  if (loading && isEditMode) {
    return (
      <div className="af-root">
        <InjectStyles />
        <div className="af-loading">
          <div className="af-spinner-large" />
          <span style={{ color: 'var(--text-muted)' }}>Cargando activo...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="af-root">
      <InjectStyles />
      <Toaster position="top-right" />

      {/* Header */}
      <header className="af-header">
        <button className="af-btn af-btn-secondary" onClick={handleCancel}>
          <FaArrowLeft size={12} /> Volver
        </button>

        <div className="af-header-title">
          {isEditMode ? <FaEdit size={14} /> : <FaPlus size={14} />}
          {isEditMode ? 'Editar Activo' : 'Nuevo Activo'}
          {isEditMode && formData.code && (
            <span className="af-badge">Código: {formData.code}</span>
          )}
        </div>
      </header>

      <div className="af-body">
        <div className="af-card">
          <div className="af-card-header">
            <h4>
              {isEditMode ? <FaEdit size={20} /> : <FaBox size={20} />}
              {isEditMode ? 'Editar Activo' : 'Registrar Nuevo Activo'}
            </h4>
          </div>

          <div className="af-card-body">
            <form onSubmit={handleSubmit}>
              {/* Información Básica */}
              <div className="af-section">
                <div className="af-section-title">
                  <FaInfoCircle size={14} /> Información Básica
                </div>
                <div className="af-grid">
                  <div className="af-form-group">
                    <label className="af-label">
                      <FaBarcode size={12} /> Código
                      <span className="required">*</span>
                    </label>
                    <input
                      type="text"
                      className="af-input"
                      name="code"
                      value={formData.code}
                      onChange={handleChange}
                      disabled={isEditMode}
                      placeholder="Ej: ACT-001"
                    />
                    <div className="af-hint">
                      <FaInfoCircle size={10} /> Código único del activo
                    </div>
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaTag size={12} /> Nombre
                      <span className="required">*</span>
                    </label>
                    <input
                      type="text"
                      className="af-input"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="Ej: Laptop Dell Latitude"
                    />
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaFolderOpen size={12} /> Categoría
                    </label>
                    <select
                      className="af-select"
                      name="category"
                      value={formData.category}
                      onChange={handleChange}
                    >
                      <option value="">Seleccionar categoría...</option>
                      {categories.map(cat => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaMapMarkerAlt size={12} /> Ubicación
                    </label>
                    <input
                      type="text"
                      className="af-input"
                      name="location"
                      value={formData.location}
                      onChange={handleChange}
                      placeholder="Ej: Oficina 201 - Piso 2"
                    />
                  </div>

                  <div className="af-full-width">
                    <div className="af-form-group">
                      <label className="af-label">
                        <FaFileAlt size={12} /> Descripción
                      </label>
                      <textarea
                        className="af-textarea"
                        name="description"
                        value={formData.description}
                        onChange={handleChange}
                        rows="3"
                        placeholder="Descripción detallada del activo..."
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Detalles del Activo */}
              <div className="af-section">
                <div className="af-section-title">
                  <FaCog size={14} /> Detalles del Activo
                </div>
                <div className="af-grid">
                  <div className="af-form-group">
                    <label className="af-label">
                      <FaBuilding size={12} /> Marca
                    </label>
                    <input
                      type="text"
                      className="af-input"
                      name="brand"
                      value={formData.brand}
                      onChange={handleChange}
                      placeholder="Ej: Dell, HP, Lenovo"
                    />
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaTag size={12} /> Modelo
                    </label>
                    <input
                      type="text"
                      className="af-input"
                      name="model"
                      value={formData.model}
                      onChange={handleChange}
                      placeholder="Ej: Latitude 5520"
                    />
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaBarcode size={12} /> Número de Serie
                    </label>
                    <input
                      type="text"
                      className="af-input"
                      name="serial_number"
                      value={formData.serial_number}
                      onChange={handleChange}
                      placeholder="Ej: SN123456789"
                    />
                  </div>
                </div>
              </div>

              {/* Estado y Condición */}
              <div className="af-section">
                <div className="af-section-title">
                  <FaChartLine size={14} /> Estado y Condición
                </div>
                <div className="af-grid">
                  <div className="af-form-group">
                    <label className="af-label">
                      <FaInfoCircle size={12} /> Estado
                    </label>
                    <select
                      className="af-select"
                      name="status"
                      value={formData.status}
                      onChange={handleChange}
                    >
                      {STATUS_CHOICES.map(choice => (
                        <option key={choice.value} value={choice.value}>
                          {choice.icon} {choice.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaCheck size={12} /> Condición
                    </label>
                    <select
                      className="af-select"
                      name="condition"
                      value={formData.condition}
                      onChange={handleChange}
                    >
                      {CONDITION_CHOICES.map(choice => (
                        <option key={choice.value} value={choice.value}>
                          {choice.icon} {choice.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaUser size={12} /> Asignado a
                    </label>
                    <input
                      type="text"
                      className="af-input"
                      name="assigned_to"
                      value={formData.assigned_to}
                      onChange={handleChange}
                      placeholder="Nombre de la persona responsable"
                    />
                  </div>
                </div>
              </div>

              {/* Información Financiera */}
              <div className="af-section">
                <div className="af-section-title">
                  <FaMoneyBillWave size={14} /> Información Financiera
                </div>
                <div className="af-grid">
                  <div className="af-form-group">
                    <label className="af-label">
                      <FaMoneyBillWave size={12} /> Precio de Compra
                    </label>
                    <input
                      type="number"
                      className="af-input"
                      name="purchase_price"
                      value={formData.purchase_price}
                      onChange={handleChange}
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                    />
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaCalendarAlt size={12} /> Fecha de Compra
                    </label>
                    <input
                      type="date"
                      className="af-input"
                      name="purchase_date"
                      value={formData.purchase_date}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaShieldAlt size={12} /> Vencimiento de Garantía
                    </label>
                    <input
                      type="date"
                      className="af-input"
                      name="warranty_expiry"
                      value={formData.warranty_expiry}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </div>

              {/* Mantenimiento */}
              <div className="af-section">
                <div className="af-section-title">
                  <FaWrench size={14} /> Mantenimiento
                </div>
                <div className="af-grid">
                  <div className="af-form-group">
                    <label className="af-label">
                      <FaCalendarAlt size={12} /> Último Mantenimiento
                    </label>
                    <input
                      type="date"
                      className="af-input"
                      name="last_maintenance"
                      value={formData.last_maintenance}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="af-form-group">
                    <label className="af-label">
                      <FaCalendarAlt size={12} /> Próximo Mantenimiento
                    </label>
                    <input
                      type="date"
                      className="af-input"
                      name="next_maintenance"
                      value={formData.next_maintenance}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="af-full-width">
                    <div className="af-form-group">
                      <label className="af-label">
                        <FaClipboardList size={12} /> Notas de Mantenimiento
                      </label>
                      <textarea
                        className="af-textarea"
                        name="maintenance_notes"
                        value={formData.maintenance_notes}
                        onChange={handleChange}
                        rows="3"
                        placeholder="Detalles sobre el mantenimiento realizado o programado..."
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Notas Adicionales */}
              <div className="af-section">
                <div className="af-section-title">
                  <FaFileAlt size={14} /> Notas Adicionales
                </div>
                <div className="af-form-group">
                  <textarea
                    className="af-textarea"
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    rows="3"
                    placeholder="Información adicional relevante sobre el activo..."
                  />
                </div>
              </div>

              {/* Botones */}
              <div className="af-actions">
                <button
                  type="button"
                  className="af-btn af-btn-secondary"
                  onClick={handleCancel}
                  disabled={loading}
                >
                  <FaTimes size={12} /> Cancelar
                </button>
                <button
                  type="submit"
                  className="af-btn af-btn-primary"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <div className="af-spinner" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <FaSave size={12} />
                      {isEditMode ? 'Actualizar Activo' : 'Guardar Activo'}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Información adicional */}
        <div style={{ 
          background: 'var(--info-light)', 
          borderRadius: 'var(--radius-md)', 
          padding: '0.75rem 1rem', 
          marginTop: '1rem',
          fontSize: '0.75rem',
          color: 'var(--info)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <FaInfoCircle size={14} />
          <span><strong>Consejo:</strong> Complete toda la información relevante para mantener un registro actualizado de sus activos. Los campos marcados con * son obligatorios.</span>
        </div>
      </div>
    </div>
  );
}

export default AssetForm;