import React, { useState, useEffect } from 'react';
import { FaSave, FaTimes, FaUser, FaEnvelope, FaLock, FaShieldAlt } from 'react-icons/fa';
import api from '../services/api';

const UserForm = ({ user, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    is_active: true,
    is_staff: false,
    is_superuser: false,
    groups: []
  });
  
  const [availableGroups, setAvailableGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username || '',
        email: user.email || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        password: '',
        is_active: user.is_active !== undefined ? user.is_active : true,
        is_staff: user.is_staff || false,
        is_superuser: user.is_superuser || false,
        groups: user.groups || []
      });
    }
    loadGroups();
  }, [user]);

  const loadGroups = async () => {
    try {
      const response = await api.get('/groups/');
      setAvailableGroups(response.data);
    } catch (err) {
      console.error('Error loading groups:', err);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleGroupChange = (groupName, checked) => {
    setFormData(prev => ({
      ...prev,
      groups: checked
        ? [...prev.groups, groupName]
        : prev.groups.filter(g => g !== groupName)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const dataToSend = { ...formData };

      // Solo enviar contraseña si se está creando un usuario nuevo o si se cambió
      if (!user && !dataToSend.password) {
        setError('La contraseña es requerida para nuevos usuarios');
        setLoading(false);
        return;
      }

      if (!dataToSend.password) {
        delete dataToSend.password;
      }

      if (user) {
        await api.put(`/users/${user.id}/`, dataToSend);
      } else {
        await api.post('/users/', dataToSend);
      }

      onSave();
    } catch (err) {
      console.error('Error saving user:', err);
      if (err.response && err.response.data) {
        const getErrorMessages = (data) => {
          if (typeof data === 'string') return [data];
          if (Array.isArray(data)) return data.flatMap(getErrorMessages);
          if (typeof data === 'object' && data !== null) {
            return Object.values(data).flatMap(getErrorMessages);
          }
          return [];
        };
        const errors = getErrorMessages(err.response.data);
        setError(errors.join(', '));
      } else {
        setError('Error al guardar usuario');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              <FaUser className="me-2" />
              {user ? 'Editar Usuario' : 'Nuevo Usuario'}
            </h5>
            <button
              type="button"
              className="btn-close"
              onClick={onClose}
            ></button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                </div>
              )}

              <div className="row">
                <div className="col-md-6">
                  <div className="mb-3">
                    <label className="form-label">
                      <FaUser className="me-1" />
                      Usuario *
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>

                <div className="col-md-6">
                  <div className="mb-3">
                    <label className="form-label">
                      <FaEnvelope className="me-1" />
                      Email
                    </label>
                    <input
                      type="email"
                      className="form-control"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </div>

              <div className="row">
                <div className="col-md-6">
                  <div className="mb-3">
                    <label className="form-label">Nombre</label>
                    <input
                      type="text"
                      className="form-control"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="col-md-6">
                  <div className="mb-3">
                    <label className="form-label">Apellido</label>
                    <input
                      type="text"
                      className="form-control"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </div>

              {!user && (
                <div className="mb-3">
                  <label className="form-label">
                    <FaLock className="me-1" />
                    Contraseña *
                  </label>
                  <input
                    type="password"
                    className="form-control"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    required={!user}
                  />
                </div>
              )}

              <div className="row">
                <div className="col-md-6">
                  <div className="mb-3">
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="is_active"
                        name="is_active"
                        checked={formData.is_active}
                        onChange={handleChange}
                      />
                      <label className="form-check-label" htmlFor="is_active">
                        Usuario activo
                      </label>
                    </div>
                  </div>
                </div>

                <div className="col-md-6">
                  <div className="mb-3">
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="is_staff"
                        name="is_staff"
                        checked={formData.is_staff}
                        onChange={handleChange}
                      />
                      <label className="form-check-label" htmlFor="is_staff">
                        Es administrador
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mb-3">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="is_superuser"
                    name="is_superuser"
                    checked={formData.is_superuser}
                    onChange={handleChange}
                  />
                  <label className="form-check-label" htmlFor="is_superuser">
                    <FaShieldAlt className="me-1" />
                    Superusuario (acceso completo)
                  </label>
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label">Grupos</label>
                <div className="row">
                  {availableGroups.map(group => (
                    <div key={group.id} className="col-md-6">
                      <div className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`group-${group.id}`}
                          checked={formData.groups.includes(group.name)}
                          onChange={(e) => handleGroupChange(group.name, e.target.checked)}
                        />
                        <label className="form-check-label" htmlFor={`group-${group.id}`}>
                          {group.name}
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={loading}
              >
                <FaTimes className="me-1" />
                Cancelar
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                    Guardando...
                  </>
                ) : (
                  <>
                    <FaSave className="me-1" />
                    {user ? 'Actualizar' : 'Crear'}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default UserForm;