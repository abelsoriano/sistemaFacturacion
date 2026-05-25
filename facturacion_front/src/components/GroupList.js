import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Edit, Trash2, Plus, Shield, ChevronLeft, ChevronRight, Key } from 'lucide-react';
import api from '../services/api';
import GroupForm from './GroupForm';
import '../css/group.css';

const GroupList = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 6;
  
  const navigate = useNavigate();

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const response = await api.get('/groups/');
      setGroups(response.data);
      setError(null);
    } catch (err) {
      setError('Error al cargar grupos');
      console.error('Error loading groups:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (groupId, groupName) => {
    if (!window.confirm(`¿Está seguro de que desea eliminar el grupo "${groupName}"?`)) {
      return;
    }

    try {
      await api.delete(`/groups/${groupId}/`);
      loadGroups();
    } catch (err) {
      setError('Error al eliminar grupo');
      console.error('Error deleting group:', err);
    }
  };

  const handleEdit = (group) => {
    setEditingGroup(group);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingGroup(null);
  };

  const handleFormSave = () => {
    loadGroups();
    handleFormClose();
  };

  const handleCancel = () => {
    navigate('/home');
  };

  const totalPages = Math.ceil(groups.length / itemsPerPage);
  const paginatedGroups = groups.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const totalPermissions = groups.reduce((total, group) => total + (group.permissions?.length || 0), 0);

  if (loading) {
    return (
      <div className="groups-page">
        <div className="groups-content">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Cargando grupos...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="groups-page">
      <div className="groups-content">
        {/* Header */}
        <div className="page-header">
          <div className="header-title">
            <div className="header-icon-wrapper">
              <Shield size={24} />
            </div>
            <div>
              <h1>Gestión de Grupos</h1>
              <p>Administra grupos de usuarios y sus permisos</p>
            </div>
          </div>
          <div className="header-actions">
            <button onClick={handleCancel} className="btn-secondary">
              Volver al inicio
            </button>
            <button onClick={() => setShowForm(true)} className="btn-primary">
              <Plus size={16} />
              Nuevo Grupo
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Users size={20} />
            </div>
            <div className="stat-info">
              <span className="stat-label">Total Grupos</span>
              <span className="stat-number">{groups.length}</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">
              <Key size={20} />
            </div>
            <div className="stat-info">
              <span className="stat-label">Permisos Totales</span>
              <span className="stat-number">{totalPermissions}</span>
            </div>
          </div>
        </div>

        {/* Groups Grid */}
        {groups.length === 0 ? (
          <div className="empty-state">
            <Shield size={48} />
            <h3>No hay grupos definidos</h3>
            <p>Crea grupos para organizar permisos de usuarios</p>
            <button onClick={() => setShowForm(true)} className="btn-primary">
              <Plus size={16} />
              Crear primer grupo
            </button>
          </div>
        ) : (
          <>
            <div className="groups-grid">
              {paginatedGroups.map(group => (
                <div key={group.id} className="group-card">
                  <div className="card-header">
                    <div className="group-avatar">
                      <Users size={20} />
                    </div>
                    <div className="group-info">
                      <h3>{group.name}</h3>
                      <span className="group-type">Grupo</span>
                    </div>
                  </div>
                  
                  <div className="card-body">
                    <div className="permissions-container">
                      <label className="permissions-label">Permisos</label>
                      <div className="permissions-list">
                        {group.permissions && group.permissions.length > 0 ? (
                          <>
                            {group.permissions.slice(0, 4).map(perm => (
                              <span key={perm.id} className="permission-tag">
                                {perm.codename}
                              </span>
                            ))}
                            {group.permissions.length > 4 && (
                              <span className="permission-tag more">
                                +{group.permissions.length - 4} más
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="no-permissions">Sin permisos asignados</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="card-footer">
                    <button
                      onClick={() => handleEdit(group)}
                      className="btn-edit"
                    >
                      <Edit size={16} />
                      Editar Grupo
                    </button>
                    <button
                      onClick={() => handleDelete(group.id, group.name)}
                      className="btn-delete"
                    >
                      <Trash2 size={16} />
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="pagination">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft size={18} />
                </button>
                <span className="page-info">
                  Página {currentPage} de {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal Form */}
      {showForm && (
        <GroupForm
          group={editingGroup}
          onClose={handleFormClose}
          onSave={handleFormSave}
        />
      )}
    </div>
  );
};

export default GroupList;