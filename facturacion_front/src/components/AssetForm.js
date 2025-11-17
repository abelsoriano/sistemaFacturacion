import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import { showSuccessAlert, showGenericAlert } from '../herpert';

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
    { value: 'available', label: 'Disponible' },
    { value: 'in_use', label: 'En Uso' },
    { value: 'maintenance', label: 'En Mantenimiento' },
    { value: 'damaged', label: 'Dañado' },
    { value: 'retired', label: 'Dado de Baja' }
  ];

  const CONDITION_CHOICES = [
    { value: 'excellent', label: 'Excelente' },
    { value: 'good', label: 'Bueno' },
    { value: 'fair', label: 'Regular' },
    { value: 'poor', label: 'Malo' }
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
      showGenericAlert('Error al cargar las categorías');
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
      showGenericAlert('Error al cargar el activo');
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

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validaciones básicas
    if (!formData.code.trim()) {
      showGenericAlert('El código es obligatorio');
      return;
    }
    if (!formData.name.trim()) {
      showGenericAlert('El nombre es obligatorio');
      return;
    }

    try {
      setLoading(true);

      // Preparar datos para enviar
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
        showSuccessAlert('Activo actualizado exitosamente');
      } else {
        await api.post('assets/', dataToSend);
        showSuccessAlert('Activo registrado exitosamente');
      }

      navigate('/assets');
    } catch (error) {
      console.error('Error al guardar activo:', error);
      if (error.response?.data) {
        const errorMsg = Object.entries(error.response.data)
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
        showGenericAlert(errorMsg || 'Error al guardar el activo');
      } else {
        showGenericAlert('Error al guardar el activo');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    navigate('/assetsManager');
  };

  if (loading && isEditMode) {
    return (
      <div className="container mt-4">
        <div className="text-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Cargando...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mt-4">
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">
                {isEditMode ? '✏️ Editar Activo' : '➕ Nuevo Activo'}
              </h4>
            </div>
            <div className="card-body">
              <form onSubmit={handleSubmit}>
                {/* Información Básica */}
                <div className="row mb-4">
                  <div className="col-12">
                    <h5 className="border-bottom pb-2 mb-3">📋 Información Básica</h5>
                  </div>
                  
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Código <span className="text-danger">*</span></label>
                    <input
                      type="text"
                      className="form-control"
                      name="code"
                      value={formData.code}
                      onChange={handleChange}
                      required
                      disabled={isEditMode}
                      placeholder="Ej: ACT-001"
                    />
                    <small className="text-muted">Código único del activo</small>
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Nombre <span className="text-danger">*</span></label>
                    <input
                      type="text"
                      className="form-control"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                      placeholder="Ej: Laptop Dell"
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Categoría</label>
                    <select
                      className="form-select"
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

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Ubicación</label>
                    <input
                      type="text"
                      className="form-control"
                      name="location"
                      value={formData.location}
                      onChange={handleChange}
                      placeholder="Ej: Oficina 201"
                    />
                  </div>

                  <div className="col-12 mb-3">
                    <label className="form-label">Descripción</label>
                    <textarea
                      className="form-control"
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      rows="3"
                      placeholder="Descripción detallada del activo..."
                    />
                  </div>
                </div>

                {/* Detalles del Activo */}
                <div className="row mb-4">
                  <div className="col-12">
                    <h5 className="border-bottom pb-2 mb-3">🔧 Detalles del Activo</h5>
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Marca</label>
                    <input
                      type="text"
                      className="form-control"
                      name="brand"
                      value={formData.brand}
                      onChange={handleChange}
                      placeholder="Ej: Dell"
                    />
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Modelo</label>
                    <input
                      type="text"
                      className="form-control"
                      name="model"
                      value={formData.model}
                      onChange={handleChange}
                      placeholder="Ej: Latitude 5520"
                    />
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Número de Serie</label>
                    <input
                      type="text"
                      className="form-control"
                      name="serial_number"
                      value={formData.serial_number}
                      onChange={handleChange}
                      placeholder="Ej: SN123456789"
                    />
                  </div>
                </div>

                {/* Estado y Condición */}
                <div className="row mb-4">
                  <div className="col-12">
                    <h5 className="border-bottom pb-2 mb-3">📊 Estado y Condición</h5>
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Estado</label>
                    <select
                      className="form-select"
                      name="status"
                      value={formData.status}
                      onChange={handleChange}
                    >
                      {STATUS_CHOICES.map(choice => (
                        <option key={choice.value} value={choice.value}>
                          {choice.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Condición</label>
                    <select
                      className="form-select"
                      name="condition"
                      value={formData.condition}
                      onChange={handleChange}
                    >
                      {CONDITION_CHOICES.map(choice => (
                        <option key={choice.value} value={choice.value}>
                          {choice.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Asignado a</label>
                    <input
                      type="text"
                      className="form-control"
                      name="assigned_to"
                      value={formData.assigned_to}
                      onChange={handleChange}
                      placeholder="Nombre de la persona"
                    />
                  </div>
                </div>

                {/* Información Financiera */}
                <div className="row mb-4">
                  <div className="col-12">
                    <h5 className="border-bottom pb-2 mb-3">💰 Información Financiera</h5>
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Precio de Compra</label>
                    <input
                      type="number"
                      className="form-control"
                      name="purchase_price"
                      value={formData.purchase_price}
                      onChange={handleChange}
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                    />
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Fecha de Compra</label>
                    <input
                      type="date"
                      className="form-control"
                      name="purchase_date"
                      value={formData.purchase_date}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-4 mb-3">
                    <label className="form-label">Vencimiento de Garantía</label>
                    <input
                      type="date"
                      className="form-control"
                      name="warranty_expiry"
                      value={formData.warranty_expiry}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                {/* Mantenimiento */}
                <div className="row mb-4">
                  <div className="col-12">
                    <h5 className="border-bottom pb-2 mb-3">🔨 Mantenimiento</h5>
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Último Mantenimiento</label>
                    <input
                      type="date"
                      className="form-control"
                      name="last_maintenance"
                      value={formData.last_maintenance}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Próximo Mantenimiento</label>
                    <input
                      type="date"
                      className="form-control"
                      name="next_maintenance"
                      value={formData.next_maintenance}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="col-12 mb-3">
                    <label className="form-label">Notas de Mantenimiento</label>
                    <textarea
                      className="form-control"
                      name="maintenance_notes"
                      value={formData.maintenance_notes}
                      onChange={handleChange}
                      rows="3"
                      placeholder="Detalles sobre el mantenimiento..."
                    />
                  </div>
                </div>

                {/* Notas Adicionales */}
                <div className="row mb-4">
                  <div className="col-12">
                    <h5 className="border-bottom pb-2 mb-3">📝 Notas Adicionales</h5>
                  </div>

                  <div className="col-12 mb-3">
                    <label className="form-label">Notas</label>
                    <textarea
                      className="form-control"
                      name="notes"
                      value={formData.notes}
                      onChange={handleChange}
                      rows="3"
                      placeholder="Información adicional relevante..."
                    />
                  </div>
                </div>

                {/* Botones */}
                <div className="row">
                  <div className="col-12">
                    <div className="d-flex gap-2 justify-content-end">
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleCancel}
                        disabled={loading}
                      >
                        ❌ Cancelar
                      </button>
                      <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={loading}
                      >
                        {loading ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2" />
                            Guardando...
                          </>
                        ) : (
                          <>💾 {isEditMode ? 'Actualizar' : 'Guardar'} Activo</>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AssetForm;