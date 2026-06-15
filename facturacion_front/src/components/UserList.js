import React, { useState, useEffect } from 'react';
import { Users, UserPlus, Edit, Trash2, Shield, User, CheckCircle, XCircle, ChevronLeft, ChevronRight, Search, Eye } from 'lucide-react';
import api from '../services/api';
import { authService } from '../services/api';
import UserForm from './UserForm';
import '../css/UserList.css';

const UserList = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;
  useEffect(() => {
    loadUsers();
    setCurrentUser(authService.getCurrentUser());
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/users/');
      setUsers(response.data);
      setError(null);
    } catch (err) {
      setError('Error al cargar usuarios');
      console.error('Error loading users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (userId, userName) => {
    if (!window.confirm(`¿Está seguro de que desea eliminar al usuario "${userName}"?`)) {
      return;
    }

    try {
      await api.delete(`/users/${userId}/`);
      loadUsers();
    } catch (err) {
      setError('Error al eliminar usuario');
      console.error('Error deleting user:', err);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingUser(null);
  };

  const handleFormSave = () => {
    loadUsers();
    handleFormClose();
  };

  const getRoleDisplay = (user) => {
    if (user.is_superuser) return { text: 'Superusuario', type: 'super' };
    if (user.is_staff) return { text: 'Administrador', type: 'admin' };
    if (user.groups && user.groups.length > 0) return { text: user.groups.join(', '), type: 'group' };
    return { text: 'Usuario', type: 'user' };
  };

  // Filtrado
  const filteredUsers = users.filter(user => {
    const matchesSearch = user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (user.first_name && user.first_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (user.last_name && user.last_name.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesStatus = statusFilter === 'all' || 
      (statusFilter === 'active' && user.is_active) ||
      (statusFilter === 'inactive' && !user.is_active);
    
    const matchesRole = roleFilter === 'all' ||
      (roleFilter === 'super' && user.is_superuser) ||
      (roleFilter === 'admin' && user.is_staff && !user.is_superuser) ||
      (roleFilter === 'user' && !user.is_staff && !user.is_superuser);
    
    return matchesSearch && matchesStatus && matchesRole;
  });

  // Paginación
  const totalPages = Math.ceil(filteredUsers.length / itemsPerPage);
  const paginatedUsers = filteredUsers.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const clearFilters = () => {
    setSearchTerm('');
    setStatusFilter('all');
    setRoleFilter('all');
    setCurrentPage(1);
  };

  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active).length,
    inactive: users.filter(u => !u.is_active).length,
    admins: users.filter(u => u.is_staff).length
  };

  if (loading) {
    return (
      <div className="users-page">
        <div className="users-content">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Cargando usuarios...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="users-page">
      <div className="users-content">
        {/* Header */}
        <div className="page-header">
          <div className="header-title">
            <div className="header-icon-wrapper">
              <Users size={24} />
            </div>
            <div>
              <h1>Gestión de Usuarios</h1>
              <p>Administra usuarios, roles y permisos del sistema</p>
            </div>
          </div>
          <div className="header-actions">
            <button onClick={() => setShowForm(true)} className="btn-primary">
              <UserPlus size={16} />
              Nuevo Usuario
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
              <span className="stat-label">Total Usuarios</span>
              <span className="stat-number">{stats.total}</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon active">
              <CheckCircle size={20} />
            </div>
            <div className="stat-info">
              <span className="stat-label">Usuarios Activos</span>
              <span className="stat-number">{stats.active}</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon inactive">
              <XCircle size={20} />
            </div>
            <div className="stat-info">
              <span className="stat-label">Usuarios Inactivos</span>
              <span className="stat-number">{stats.inactive}</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon admin">
              <Shield size={20} />
            </div>
            <div className="stat-info">
              <span className="stat-label">Administradores</span>
              <span className="stat-number">{stats.admins}</span>
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="search-section">
          <div className="search-bar">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Buscar por nombre, usuario o email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button onClick={() => setSearchTerm('')} className="clear-btn">
                ×
              </button>
            )}
          </div>

          <div className="filters-bar">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">Todos los estados</option>
              <option value="active">Activos</option>
              <option value="inactive">Inactivos</option>
            </select>

            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">Todos los roles</option>
              <option value="super">Superusuario</option>
              <option value="admin">Administrador</option>
              <option value="user">Usuario</option>
            </select>

            {(searchTerm || statusFilter !== 'all' || roleFilter !== 'all') && (
              <button onClick={clearFilters} className="clear-filters">
                Limpiar filtros
              </button>
            )}
          </div>
        </div>

        {/* Users Table */}
        {filteredUsers.length === 0 ? (
          <div className="empty-state">
            <Users size={48} />
            <h3>No se encontraron usuarios</h3>
            <p>Intenta con otros filtros o crea un nuevo usuario</p>
            <button onClick={clearFilters} className="btn-secondary">
              Limpiar filtros
            </button>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table className="users-table">
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Email</th>
                    <th>Nombre Completo</th>
                    <th>Rol</th>
                    <th>Estado</th>
                    <th>Último Login</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedUsers.map(user => {
                    const role = getRoleDisplay(user);
                    return (
                      <tr key={user.id}>
                        <td className="username-cell" data-label="Usuario">
                          <div className="username-wrapper">
                            <div className="user-avatar">
                              <User size={16} />
                            </div>
                            <span className="username">{user.username}</span>
                          </div>
                        </td>
                        <td className="email-cell" data-label="Email">{user.email || '-'}</td>
                        <td data-label="Nombre Completo">
                          {user.first_name || user.last_name
                            ? `${user.first_name} ${user.last_name}`.trim()
                            : '-'}
                        </td>
                        <td data-label="Rol">
                          <span className={`role-badge ${role.type}`}>
                            <Shield size={12} />
                            {role.text}
                          </span>
                        </td>
                        <td data-label="Estado">
                          <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                            {user.is_active ? (
                              <>
                                <CheckCircle size={12} />
                                Activo
                              </>
                            ) : (
                              <>
                                <XCircle size={12} />
                                Inactivo
                              </>
                            )}
                          </span>
                        </td>
                        <td className="last-login" data-label="Último Login">
                          {user.last_login
                            ? new Date(user.last_login).toLocaleDateString('es-ES', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric'
                              })
                            : 'Nunca'}
                        </td>
                        <td data-label="Acciones">
                          <div className="action-buttons">
                            <button
                              onClick={() => setSelectedUser(user)}
                              className="icon-btn view"
                              title="Ver usuario"
                            >
                              <Eye size={16} />
                            </button>
                            <button
                              onClick={() => handleEdit(user)}
                              className="icon-btn edit"
                              title="Editar usuario"
                            >
                              <Edit size={16} />
                            </button>
                            {currentUser && currentUser.id !== user.id && (
                              <button
                                onClick={() => handleDelete(user.id, user.username)}
                                className="icon-btn delete"
                                title="Eliminar usuario"
                              >
                                <Trash2 size={16} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
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
        <UserForm
          user={editingUser}
          onClose={handleFormClose}
          onSave={handleFormSave}
        />
      )}

      {selectedUser && (
        <div className="user-detail-overlay" onClick={(e) => e.target === e.currentTarget && setSelectedUser(null)}>
          <section className="user-detail-modal" role="dialog" aria-modal="true" aria-labelledby="user-detail-title">
            <div className="user-detail-header">
              <div className="username-wrapper">
                <div className="user-avatar detail">
                  <User size={18} />
                </div>
                <div>
                  <h2 id="user-detail-title">{selectedUser.username}</h2>
                  <p>{selectedUser.email || 'Sin email registrado'}</p>
                </div>
              </div>
              <button className="user-detail-close" onClick={() => setSelectedUser(null)}>×</button>
            </div>
            <div className="user-detail-grid">
              <div>
                <span>Nombre</span>
                <strong>{`${selectedUser.first_name || ''} ${selectedUser.last_name || ''}`.trim() || '-'}</strong>
              </div>
              <div>
                <span>Rol</span>
                <strong>{getRoleDisplay(selectedUser).text}</strong>
              </div>
              <div>
                <span>Estado</span>
                <strong>{selectedUser.is_active ? 'Activo' : 'Inactivo'}</strong>
              </div>
              <div>
                <span>Último login</span>
                <strong>{selectedUser.last_login ? new Date(selectedUser.last_login).toLocaleString('es-ES') : 'Nunca'}</strong>
              </div>
            </div>
            <div className="user-detail-actions">
              <button className="btn-secondary" onClick={() => setSelectedUser(null)}>Cerrar</button>
              <button className="btn-primary" onClick={() => { setSelectedUser(null); handleEdit(selectedUser); }}>Editar usuario</button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
};

export default UserList;
