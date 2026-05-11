import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import { 
  FaUser, FaSave, FaArrowLeft, FaPlus, FaTrash, 
  FaEnvelope, FaPhone, FaMapMarkerAlt, FaIdCard, 
  FaStar, FaUserPlus, FaEdit
} from 'react-icons/fa';

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
      navigate('/clients');
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
      
      // Preguntar si quiere crear otro
      if (!isEditMode) {
        const result = await Swal.fire({
          title: '¿Cliente creado!',
          text: '¿Deseas crear otro cliente?',
          icon: 'success',
          showCancelButton: true,
          confirmButtonText: 'Sí, crear otro',
          cancelButtonText: 'Volver al listado'
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
      
      navigate('/clients');
    } catch (error) {
      console.error('Error guardando cliente:', error);
      if (error.response?.status === 400) {
        const backendErrors = error.response.data;
        const formattedErrors = {};
        Object.keys(backendErrors).forEach(key => {
          formattedErrors[key] = backendErrors[key].join(', ');
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
    if (Object.values(formData).some(v => v && v.trim())) {
      Swal.fire({
        title: '¿Cancelar?',
        text: 'Los cambios no guardados se perderán',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#d33',
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

  // Tipos de cliente
  const clientTypes = [
    { value: 'occasional', label: '🔄 Ocasional', description: 'Cliente que compra esporádicamente' },
    { value: 'regular', label: '📌 Regular', description: 'Cliente con compras frecuentes' },
    { value: 'frequent', label: '⭐ Frecuente', description: 'Cliente VIP con volumen alto de compras' }
  ];

  return (
    <div className="container py-4" style={{ backgroundColor: '#f8f9fa', minHeight: '100vh' }}>
      <Toaster position="top-right" />
      
      <div className="row justify-content-center">
        <div className="col-lg-8">
          <div className="card shadow-sm border-0">
            <div className="card-header bg-primary text-white py-3">
              <div className="d-flex align-items-center">
                {isEditMode ? <FaEdit size={24} /> : <FaUserPlus size={24} />}
                <h3 className="mb-0 ms-2">
                  {isEditMode ? 'Editar Cliente' : 'Nuevo Cliente'}
                </h3>
              </div>
              <p className="mb-0 mt-1 small opacity-75">
                {isEditMode 
                  ? 'Actualice la información del cliente' 
                  : 'Registre un nuevo cliente en el sistema'}
              </p>
            </div>
            
            <div className="card-body p-4">
              <form onSubmit={handleSubmit}>
                {/* Nombre */}
                <div className="mb-4">
                  <label className="form-label fw-bold">
                    <FaUser className="me-2 text-primary" />
                    Nombre completo *
                  </label>
                  <input
                    type="text"
                    className={`form-control form-control-lg ${errors.name ? 'is-invalid' : ''}`}
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="Ej: Juan Pérez González"
                    disabled={loading}
                  />
                  {errors.name && (
                    <div className="invalid-feedback">{errors.name}</div>
                  )}
                </div>
                
                <div className="row">
                  {/* Email */}
                  <div className="col-md-6 mb-4">
                    <label className="form-label fw-bold">
                      <FaEnvelope className="me-2 text-primary" />
                      Correo electrónico
                    </label>
                    <input
                      type="email"
                      className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="cliente@ejemplo.com"
                      disabled={loading}
                    />
                    {errors.email && (
                      <div className="invalid-feedback">{errors.email}</div>
                    )}
                    <small className="text-muted">Opcional pero recomendado</small>
                  </div>
                  
                  {/* Teléfono */}
                  <div className="col-md-6 mb-4">
                    <label className="form-label fw-bold">
                      <FaPhone className="me-2 text-primary" />
                      Teléfono
                    </label>
                    <input
                      type="tel"
                      className={`form-control ${errors.phone ? 'is-invalid' : ''}`}
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      placeholder="0999 123 456"
                      disabled={loading}
                    />
                    {errors.phone && (
                      <div className="invalid-feedback">{errors.phone}</div>
                    )}
                    <small className="text-muted">Número de contacto</small>
                  </div>
                </div>
                
                <div className="row">
                  {/* RUC/CI */}
                  <div className="col-md-6 mb-4">
                    <label className="form-label fw-bold">
                      <FaIdCard className="me-2 text-primary" />
                      RUC / CI
                    </label>
                    <input
                      type="text"
                      className={`form-control ${errors.ruc_ci ? 'is-invalid' : ''}`}
                      name="ruc_ci"
                      value={formData.ruc_ci}
                      onChange={handleChange}
                      placeholder="1712345678001"
                      disabled={loading}
                    />
                    {errors.ruc_ci && (
                      <div className="invalid-feedback">{errors.ruc_ci}</div>
                    )}
                    <small className="text-muted">Opcional para facturación</small>
                  </div>
                  
                  {/* Tipo de Cliente */}
                  <div className="col-md-6 mb-4">
                    <label className="form-label fw-bold">
                      <FaStar className="me-2 text-primary" />
                      Tipo de Cliente
                    </label>
                    <select
                      className="form-select"
                      name="client_type"
                      value={formData.client_type}
                      onChange={handleChange}
                      disabled={loading}
                    >
                      {clientTypes.map(type => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                    <small className="text-muted">
                      {clientTypes.find(t => t.value === formData.client_type)?.description}
                    </small>
                  </div>
                </div>
                
                {/* Dirección */}
                <div className="mb-4">
                  <label className="form-label fw-bold">
                    <FaMapMarkerAlt className="me-2 text-primary" />
                    Dirección
                  </label>
                  <textarea
                    className={`form-control ${errors.address ? 'is-invalid' : ''}`}
                    name="address"
                    value={formData.address}
                    onChange={handleChange}
                    rows="3"
                    placeholder="Dirección completa del cliente"
                    disabled={loading}
                  ></textarea>
                  {errors.address && (
                    <div className="invalid-feedback">{errors.address}</div>
                  )}
                </div>
                
                {/* Botones */}
                <div className="d-flex gap-2 justify-content-end border-top pt-4">
                  <button
                    type="button"
                    className="btn btn-outline-secondary px-4"
                    onClick={handleCancel}
                    disabled={loading}
                  >
                    <FaArrowLeft className="me-2" />
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary px-4"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <FaSave className="me-2" />
                        {isEditMode ? 'Actualizar' : 'Guardar'} Cliente
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
          
          {/* Información adicional */}
          <div className="card bg-light border-0 mt-3">
            <div className="card-body">
              <small className="text-muted">
                <strong>ℹ️ Información:</strong> Los campos marcados con * son obligatorios.
                El cliente puede ser creado sin RUC/CI para ventas ocasionales.
                Los clientes frecuentes tendrán beneficios especiales.
              </small>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientForm;