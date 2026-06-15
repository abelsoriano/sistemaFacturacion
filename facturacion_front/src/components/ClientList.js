import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import { 
  FaUsers, FaPlus, FaEdit, FaTrash, FaSearch, 
  FaEye, FaFileExport, FaUser, FaPhone, FaEnvelope,
  FaMapMarkerAlt, FaIdCard, FaStar, FaFilter,
  FaArrowLeft, FaHashtag, FaMoneyBillWave, FaFileInvoice,
  FaChevronLeft, FaChevronRight, FaTimes  
} from 'react-icons/fa';
import { format } from 'date-fns';
import '../css/listaCliente.css';
import { FINANCIAL_TOTALS_PERMISSIONS, userHasAnyPermission } from '../utils/permissions';


/* ─── Helper Functions ─────────────────────────────────────────────────── */
const formatMoney = (n) => `$${(+n || 0).toFixed(2)}`;

const getInitials = (name = "") =>
  name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2) || "?";

const getTypeBadge = (type) => {
  switch(type) {
    case 'frequent':
      return <span className="type-badge type-frequent"><FaStar size={10} /> Frecuente</span>;
    case 'regular':
      return <span className="type-badge type-regular">Regular</span>;
    default:
      return <span className="type-badge type-occasional">Ocasional</span>;
  }
};

/* ─── Main Component ───────────────────────────────────────────────────── */
const ClientList = () => {
  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
  const canViewSalesTotals = userHasAnyPermission(currentUser, FINANCIAL_TOTALS_PERMISSIONS);
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [selectedClient, setSelectedClient] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // Cargar clientes
  const loadClients = async () => {
    setLoading(true);
    try {
      const response = await api.get('clients/');
      setClients(response.data);
    } catch (error) {
      console.error('Error cargando clientes:', error);
      toast.error('Error al cargar los clientes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  // Filtrar clientes
  const filteredClients = clients.filter(client => {
    const matchesSearch = 
      client.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.phone?.includes(searchTerm) ||
      client.ruc_ci?.includes(searchTerm);
    
    if (filterType === 'all') return matchesSearch;
    return matchesSearch && client.client_type === filterType;
  });

  // Paginación
  const totalPages = Math.ceil(filteredClients.length / pageSize);
  const paginatedClients = filteredClients.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterType]);

  // Estadísticas
  const totalClients = clients.length;
  const frequentCount = clients.filter(c => c.client_type === 'frequent').length;
  const regularCount = clients.filter(c => c.client_type === 'regular').length;
  const totalSpent = clients.reduce((sum, c) => sum + (c.total_spent || 0), 0);

  // Eliminar cliente
  const handleDelete = async (client) => {
    const result = await Swal.fire({
      title: '¿Eliminar cliente?',
      html: `¿Estás seguro de eliminar a <strong>${client.name}</strong>?<br/>
             <small>Esta acción no se puede deshacer.</small>`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#6b7280',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (result.isConfirmed) {
      try {
        await api.delete(`clients/${client.id}/`);
        toast.success('Cliente eliminado correctamente');
        loadClients();
      } catch (error) {
        if (error.response?.status === 409) {
          toast.error('No se puede eliminar el cliente porque tiene facturas asociadas');
        } else {
          toast.error('Error al eliminar el cliente');
        }
      }
    }
  };

  // Ver detalles del cliente
  const handleViewDetails = (client) => {
    setSelectedClient(client);
    setShowDetailsModal(true);
  };

  // Exportar a CSV
  const exportToCSV = () => {
    const headers = [
      'ID',
      'Nombre',
      'Email',
      'Teléfono',
      'Dirección',
      'RUC/CI',
      'Tipo',
      'Facturas',
      ...(canViewSalesTotals ? ['Gastado'] : []),
    ];
    const data = filteredClients.map(client => [
      client.id,
      client.name,
      client.email || '',
      client.phone || '',
      client.address || '',
      client.ruc_ci || '',
      client.client_type === 'frequent' ? 'Frecuente' : client.client_type === 'regular' ? 'Regular' : 'Ocasional',
      client.total_invoices || 0,
      ...(canViewSalesTotals ? [client.total_spent ? formatMoney(client.total_spent) : '$0.00'] : []),
    ]);

    const csvContent = [headers, ...data].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.setAttribute('download', `clientes_${format(new Date(), 'yyyy-MM-dd')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success('Exportación completada');
  };

  // Reset filters
  const resetFilters = () => {
    setSearchTerm('');
    setFilterType('all');
  };

  const hasActiveFilters = searchTerm !== '' || filterType !== 'all';

  if (loading) {
    return (
      <div className="cl-root">
        <div className="cl-state-center">
          <div className="cl-spinner" />
          <span style={{ color: "var(--text-muted)" }}>Cargando clientes...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="cl-root">
      <Toaster position="top-right" />

      {/* Modal de detalles */}
      {showDetailsModal && selectedClient && (
        <div className="cl-modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowDetailsModal(false)}>
          <div className="cl-modal">
            <div className="cl-modal-header">
              <h5 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FaUser size={16} /> Detalles del Cliente
              </h5>
              <button 
                onClick={() => setShowDetailsModal(false)}
                style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.25rem' }}
              >
                ×
              </button>
            </div>
            <div className="cl-modal-body">
              <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
                <div className="cl-avatar" style={{ width: '4rem', height: '4rem', fontSize: '1.25rem', margin: '0 auto' }}>
                  {getInitials(selectedClient.name)}
                </div>
                <h4 style={{ marginTop: '0.75rem', marginBottom: '0.25rem' }}>{selectedClient.name}</h4>
                {getTypeBadge(selectedClient.client_type)}
              </div>
              
              <div className="cl-info-row">
                <span className="cl-info-label"><FaEnvelope size={11} /> Email</span>
                <span className="cl-info-value">{selectedClient.email || 'No registrado'}</span>
              </div>
              <div className="cl-info-row">
                <span className="cl-info-label"><FaPhone size={11} /> Teléfono</span>
                <span className="cl-info-value">{selectedClient.phone || 'No registrado'}</span>
              </div>
              <div className="cl-info-row">
                <span className="cl-info-label"><FaMapMarkerAlt size={11} /> Dirección</span>
                <span className="cl-info-value">{selectedClient.address || 'No registrada'}</span>
              </div>
              <div className="cl-info-row">
                <span className="cl-info-label"><FaIdCard size={11} /> RUC/CI</span>
                <span className="cl-info-value">{selectedClient.ruc_ci || 'No registrado'}</span>
              </div>
              
              <div className="cl-info-row">
                <span className="cl-info-label"><FaFileInvoice size={11} /> Facturas</span>
                <span className="cl-info-value"><strong>{selectedClient.total_invoices || 0}</strong> facturas</span>
              </div>
              {canViewSalesTotals && (
              <div className="cl-info-row">
                <span className="cl-info-label"><FaMoneyBillWave size={11} /> Total gastado</span>
                <span className="cl-info-value" style={{ color: 'var(--success)', fontWeight: 700 }}>
                  {formatMoney(selectedClient.total_spent)}
                </span>
              </div>
              )}
            </div>
            <div className="cl-modal-footer">
              <button className="cl-btn cl-btn-outline cl-btn-sm" onClick={() => setShowDetailsModal(false)}>
                Cerrar
              </button>
              <button 
                className="cl-btn cl-btn-primary cl-btn-sm"
                onClick={() => {
                  setShowDetailsModal(false);
                  navigate(`/clients/${selectedClient.id}/edit`);
                }}
              >
                <FaEdit size={12} /> Editar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="cl-header">
        <button className="cl-btn cl-btn-outline cl-btn-sm" onClick={() => navigate('/home')}>
          <FaArrowLeft size={12} /> Volver
        </button>

        <div className="cl-header-title">
          <FaUsers size={14} style={{ color: 'var(--primary)' }} />
          Clientes
          <span className="cl-badge">{totalClients}</span>
        </div>

        <div className="cl-header-actions">
          <button className="cl-btn cl-btn-outline cl-btn-sm" onClick={exportToCSV}>
            <FaFileExport size={11} /> Exportar
          </button>
          <button 
            className="cl-btn cl-btn-primary cl-btn-sm"
            onClick={() => navigate('/clients/new')}
          >
            <FaPlus size={11} /> Nuevo cliente
          </button>
        </div>
      </header>

      <div className="cl-body">
        {/* Stats Cards */}
        <div className="cl-stats">
          <div className="cl-stat-card">
            <div className="cl-stat-label">Total Clientes</div>
            <div className="cl-stat-value primary">{totalClients}</div>
            <div className="cl-stat-sub">registrados</div>
          </div>
          <div className="cl-stat-card">
            <div className="cl-stat-label">Frecuentes</div>
            <div className="cl-stat-value primary">{frequentCount}</div>
            <div className="cl-stat-sub">⭐ clientes frecuentes</div>
          </div>
          <div className="cl-stat-card">
            <div className="cl-stat-label">Regulares</div>
            <div className="cl-stat-value">{regularCount}</div>
            <div className="cl-stat-sub">clientes regulares</div>
          </div>
          {canViewSalesTotals && (
          <div className="cl-stat-card">
            <div className="cl-stat-label">Total Gastado</div>
            <div className="cl-stat-value success">{formatMoney(totalSpent)}</div>
            <div className="cl-stat-sub">en todas las facturas</div>
          </div>
          )}
        </div>

        {/* Filter Panel */}
        <div className="cl-filter-card">
          <div className="cl-filter-header">
            <div className="cl-filter-title">
              <FaFilter size={11} /> Filtros
              {hasActiveFilters && (
                <span className="cl-badge" style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
                  activos
                </span>
              )}
            </div>
            {hasActiveFilters && (
              <button className="cl-btn cl-btn-outline cl-btn-sm" onClick={resetFilters}>
                <FaTimes size={10} /> Limpiar
              </button>
            )}
          </div>
          <div className="cl-filter-body">
            <div className="cl-search-wrapper">
              <FaSearch className="cl-search-icon" />
              <input
                type="text"
                className="cl-search-input"
                placeholder="Buscar por nombre, email, teléfono o RUC..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <select 
              className="cl-select"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              style={{ width: '100%' }}
            >
              <option value="all">Todos los clientes</option>
              <option value="frequent">⭐ Clientes frecuentes</option>
              <option value="regular">📌 Clientes regulares</option>
              <option value="occasional">🔄 Clientes ocasionales</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="cl-table-card">
          <div className="cl-table-header">
            <div className="cl-table-title">
              <FaUsers size={12} /> Clientes
              <span className="cl-badge">{filteredClients.length} resultados</span>
            </div>
            {canViewSalesTotals && filteredClients.length > 0 && (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)' }}>
                Total: {formatMoney(filteredClients.reduce((sum, c) => sum + (c.total_spent || 0), 0))}
              </span>
            )}
          </div>

          <div className="cl-table-wrapper">
            <table className="cl-table">
              <thead>
                <tr>
                  <th><FaHashtag size={10} /> #</th>
                  <th><FaUser size={10} /> Cliente</th>
                  <th><FaPhone size={10} /> Contacto</th>
                  <th><FaIdCard size={10} /> RUC/CI</th>
                  <th>Tipo</th>
                  <th className="text-end"><FaFileInvoice size={10} /> Facturas</th>
                  {canViewSalesTotals && <th className="text-end"><FaMoneyBillWave size={10} /> Gastado</th>}
                  <th className="text-end">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {paginatedClients.length === 0 ? (
                  <tr>
                    <td colSpan={canViewSalesTotals ? "8" : "7"}>
                      <div className="cl-empty">
                        <FaUsers size={48} />
                        <p>
                          {hasActiveFilters
                            ? "No hay resultados con los filtros actuales"
                            : "No hay clientes registrados"}
                        </p>
                        {hasActiveFilters && (
                          <button className="cl-btn cl-btn-outline cl-btn-sm" onClick={resetFilters}>
                            Limpiar filtros
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ) : (
                  paginatedClients.map((client, idx) => (
                    <tr key={client.id}>
                      <td data-label="#">{(currentPage - 1) * pageSize + idx + 1}</td>
                      <td data-label="Cliente">
                        <div className="cl-client-cell">
                          <div className="cl-avatar">{getInitials(client.name)}</div>
                          <div className="cl-client-main">
                            <strong className="cl-client-name">{client.name}</strong>
                            <span className="cl-client-meta">{client.email || client.phone || 'Sin contacto registrado'}</span>
                          </div>
                        </div>
                      </td>
                      <td data-label="Contacto">
                        <div className="cl-contact-stack">
                          {client.email && <div className="cl-contact-line"><FaEnvelope size={10} />{client.email}</div>}
                          {client.phone && <div className="cl-contact-line"><FaPhone size={10} />{client.phone}</div>}
                          {!client.email && !client.phone && <span style={{ color: 'var(--text-faint)' }}>—</span>}
                        </div>
                      </td>
                      <td data-label="RUC/CI" style={{ fontFamily: 'var(--mono)', fontSize: '0.75rem' }}>{client.ruc_ci || '—'}</td>
                      <td data-label="Tipo">{getTypeBadge(client.client_type)}</td>
                      <td data-label="Facturas" className="text-end">
                        <span className="cl-badge" style={{ background: 'var(--info-light)', color: 'var(--info)' }}>
                          {client.total_invoices || 0}
                        </span>
                      </td>
                      {canViewSalesTotals && (
                      <td data-label="Gastado" className="text-end">
                        <strong style={{ color: 'var(--success)' }}>{formatMoney(client.total_spent)}</strong>
                      </td>
                      )}
                      <td data-label="Acciones" className="text-end">
                        <div className="cl-actions">
                          <div className="cl-action-group">
                            <button className="cl-action-btn btn-view" onClick={() => handleViewDetails(client)} title="Ver detalles">
                              <FaEye size={12} />
                            </button>
                            <button className="cl-action-btn btn-edit" onClick={() => navigate(`/clients/${client.id}/edit`)} title="Editar">
                              <FaEdit size={12} />
                            </button>
                          </div>
                          <div className="cl-action-group">
                            <button className="cl-action-btn btn-delete" onClick={() => handleDelete(client)} title="Eliminar">
                              <FaTrash size={12} />
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {!loading && filteredClients.length > 0 && (
            <div className="cl-pagination">
              <div className="cl-pagination-info">
                Mostrando {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, filteredClients.length)} de {filteredClients.length} clientes
              </div>
              <div className="cl-pagination-buttons">
                <button
                  className="cl-page-btn"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(currentPage - 1)}
                >
                  <FaChevronLeft size={10} /> Anterior
                </button>
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      className={`cl-page-btn ${currentPage === pageNum ? 'active' : ''}`}
                      onClick={() => setCurrentPage(pageNum)}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  className="cl-page-btn"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(currentPage + 1)}
                >
                  Siguiente <FaChevronRight size={10} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ClientList;
