import React, { useState, useEffect } from 'react';
import { FaSave, FaTimes, FaUsers, FaShieldAlt } from 'react-icons/fa';
import api from '../services/api';

const GroupForm = ({ group, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    permissions: []
  });
  const [availablePermissions, setAvailablePermissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (group) {
      setFormData({
        name: group.name || '',
        permissions: group.permissions ? group.permissions.map(p => p.id) : []
      });
    }
    loadPermissions();
  }, [group]);

  const loadPermissions = async () => {
    try {
      const response = await api.get('/permissions/');
      setAvailablePermissions(response.data);
    } catch (err) {
      console.error('Error loading permissions:', err);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePermissionChange = (permissionId, checked) => {
    setFormData(prev => ({
      ...prev,
      permissions: checked
        ? [...prev.permissions, permissionId]
        : prev.permissions.filter(id => id !== permissionId)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const dataToSend = {
        name: formData.name,
        permissions: formData.permissions
      };

      if (group) {
        await api.put(`/groups/${group.id}/`, dataToSend);
      } else {
        await api.post('/groups/', dataToSend);
      }

      onSave();
    } catch (err) {
      console.error('Error saving group:', err);
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
        setError('Error al guardar grupo');
      }
    } finally {
      setLoading(false);
    }
  };

  // Agrupar permisos por aplicación
  const groupedPermissions = availablePermissions.reduce((acc, perm) => {
    const app = perm.app_label;
    if (!acc[app]) {
      acc[app] = [];
    }
    acc[app].push(perm);
    return acc;
  }, {});

  return (
    <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-xl">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              <FaUsers className="me-2" />
              {group ? 'Editar Grupo' : 'Nuevo Grupo'}
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

              <div className="mb-3">
                <label className="form-label">
                  <FaUsers className="me-1" />
                  Nombre del Grupo *
                </label>
                <input
                  type="text"
                  className="form-control"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  placeholder="Ej: Administradores, Vendedores, etc."
                />
              </div>

              <div className="mb-3">
                <label className="form-label">
                  <FaShieldAlt className="me-1" />
                  Permisos
                </label>
                <div className="border rounded p-3" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                  {Object.keys(groupedPermissions).map(app => (
                    <div key={app} className="mb-3">
                      <h6 className="text-primary mb-2">{app}</h6>
                      <div className="row">
                        {groupedPermissions[app].map(permission => (
                          <div key={permission.id} className="col-md-6 col-lg-4">
                            <div className="form-check">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id={`perm-${permission.id}`}
                                checked={formData.permissions.includes(permission.id)}
                                onChange={(e) => handlePermissionChange(permission.id, e.target.checked)}
                              />
                              <label className="form-check-label" htmlFor={`perm-${permission.id}`}>
                                <small>{permission.name}</small>
                              </label>
                            </div>
                          </div>
                        ))}
                      </div>
                      <hr />
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
                    {group ? 'Actualizar' : 'Crear'}
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

export default GroupForm;