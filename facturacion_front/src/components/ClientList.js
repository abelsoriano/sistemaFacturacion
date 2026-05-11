import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import { 
  FaUsers, FaPlus, FaEdit, FaTrash, FaSearch, 
  FaEye, FaFileExport, FaUser, FaPhone, FaEnvelope,
  FaMapMarkerAlt, FaIdCard, FaStar, FaFilter
} from 'react-icons/fa';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const ClientList = () => {
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
    if (filterType === 'regular') return matchesSearch && client.client_type === 'regular';
    if (filterType === 'frequent') return matchesSearch && client.client_type === 'frequent';
    if (filterType === 'occasional') return matchesSearch && client.client_type === 'occasional';
    
    return matchesSearch;
  });

  // Paginación
  const totalPages = Math.ceil(filteredClients.length / pageSize);
  const paginatedClients = filteredClients.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Eliminar cliente
  const handleDelete = async (client) => {
    const result = await Swal.fire({
      title: '¿Eliminar cliente?',
      html: `¿Estás seguro de eliminar a <strong>${client.name}</strong>?<br/>
             <small class="text-muted">Esta acción no se puede deshacer.</small>`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (result.isConfirmed) {
      try {
        await api.delete(`clients/${client.id}/`);
        toast.success('Cliente eliminado correctamente');
        loadClients();
      } catch (error) {
        console.error('Error:', error);
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
    const headers = ['ID', 'Nombre', 'Email', 'Teléfono', 'Dirección', 'RUC/CI', 'Tipo', 'Facturas', 'Gastado'];
    const data = filteredClients.map(client => [
      client.id,
      client.name,
      client.email || '',
      client.phone || '',
      client.address || '',
      client.ruc_ci || '',
      client.client_type === 'frequent' ? 'Frecuente' : client.client_type === 'regular' ? 'Regular' : 'Ocasional',
      client.total_invoices || 0,
      client.total_spent ? `$${client.total_spent.toFixed(2)}` : '$0.00'
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

  // Obtener badge del tipo de cliente
  const getClientTypeBadge = (type) => {
    switch(type) {
      case 'frequent':
        return <span className="badge bg-success"><FaStar className="me-1" /> Frecuente</span>;
      case 'regular':
        return <span className="badge bg-primary">Regular</span>;
      default:
        return <span className="badge bg-secondary">Ocasional</span>;
    }
  };

  return (
    <div className="container-fluid px-4 py-4" style={{ backgroundColor: '#f8f9fa', minHeight: '100vh' }}>
      <Toaster position="top-right" />
      
      {/* Modal de detalles */}
      {showDetailsModal && selectedClient && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header bg-primary text-white">
                <h5 className="modal-title">
                  <FaUser className="me-2" />
                  Detalles del Cliente
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowDetailsModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="text-center mb-3">
                  <div className="bg-primary bg-opacity-10 rounded-circle d-inline-flex p-3">
                    <FaUser size={48} className="text-primary" />
                  </div>
                  <h4 className="mt-2">{selectedClient.name}</h4>
                  {getClientTypeBadge(selectedClient.client_type)}
                </div>
                
                <div className="row g-3">
                  <div className="col-md-6">
                    <div className="text-muted small">Email</div>
                    <div><FaEnvelope className="me-2 text-muted" /> {selectedClient.email || 'No registrado'}</div>
                  </div>
                  <div className="col-md-6">
                    <div className="text-muted small">Teléfono</div>
                    <div><FaPhone className="me-2 text-muted" /> {selectedClient.phone || 'No registrado'}</div>
                  </div>
                  <div className="col-12">
                    <div className="text-muted small">Dirección</div>
                    <div><FaMapMarkerAlt className="me-2 text-muted" /> {selectedClient.address || 'No registrada'}</div>
                  </div>
                  <div className="col-md-6">
                    <div className="text-muted small">RUC/CI</div>
                    <div><FaIdCard className="me-2 text-muted" /> {selectedClient.ruc_ci || 'No registrado'}</div>
                  </div>
                  <div className="col-md-6">
                    <div className="text-muted small">Facturas</div>
                    <div><strong>{selectedClient.total_invoices || 0}</strong> facturas</div>
                  </div>
                  <div className="col-md-6">
                    <div className="text-muted small">Total gastado</div>
                    <div className="text-success fw-bold">${(selectedClient.total_spent || 0).toFixed(2)}</div>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn btn-primary" onClick={() => {
                  setShowDetailsModal(false);
                  navigate(`/edit-client/${selectedClient.id}`);
                }}>
                  <FaEdit className="me-1" /> Editar
                </button>
                <button className="btn btn-secondary" onClick={() => setShowDetailsModal(false)}>Cerrar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-3">
        <div>
          <h2 className="mb-0">
            <FaUsers className="me-2 text-primary" />
            Gestión de Clientes
          </h2>
          <p className="text-muted mt-1">Administra tus clientes, visualiza sus compras y estadísticas</p>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-outline-success" onClick={exportToCSV}>
            <FaFileExport className="me-2" /> Exportar CSV
          </button>
          <button 
            className="btn btn-primary"
            onClick={() => navigate('/clients/new')}
          >
            <FaPlus className="me-2" /> Nuevo Cliente
          </button>
        </div>
      </div>

      {/* Filtros y búsqueda */}
      <div className="card shadow-sm border-0 mb-4">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <div className="input-group">
                <span className="input-group-text bg-white">
                  <FaSearch className="text-primary" />
                </span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Buscar por nombre, email, teléfono o RUC..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-4">
              <select 
                className="form-select"
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
              >
                <option value="all">Todos los clientes</option>
                <option value="frequent">⭐ Clientes frecuentes</option>
                <option value="regular">📌 Clientes regulares</option>
                <option value="occasional">🔄 Clientes ocasionales</option>
              </select>
            </div>
            <div className="col-md-2">
              <div className="text-muted text-end">
                <small>{filteredClients.length} clientes encontrados</small>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabla de clientes */}
      <div className="card shadow-sm border-0">
        <div className="card-body p-0">
          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Cargando...</span>
              </div>
              <p className="mt-2 text-muted">Cargando clientes...</p>
            </div>
          ) : paginatedClients.length === 0 ? (
            <div className="text-center py-5">
              <FaUsers size={48} className="text-muted opacity-25 mb-3" />
              <p className="text-muted">No hay clientes registrados</p>
              <button className="btn btn-primary" onClick={() => navigate('/clients/new')}>
                <FaPlus className="me-2" /> Crear primer cliente
              </button>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th>#</th>
                    <th>Cliente</th>
                    <th>Contacto</th>
                    <th>RUC/CI</th>
                    <th>Tipo</th>
                    <th className="text-end">Facturas</th>
                    <th className="text-end">Total Gastado</th>
                    <th className="text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedClients.map((client, index) => (
                    <tr key={client.id}>
                      <td>{(currentPage - 1) * pageSize + index + 1}</td>
                      <td>
                        <div className="d-flex align-items-center">
                          <div className="bg-primary bg-opacity-10 rounded-circle p-2 me-2">
                            <FaUser size={16} className="text-primary" />
                          </div>
                          <div>
                            <strong>{client.name}</strong>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="small">
                          {client.email && <div><FaEnvelope className="text-muted me-1" size={12}/> {client.email}</div>}
                          {client.phone && <div><FaPhone className="text-muted me-1" size={12}/> {client.phone}</div>}
                          {!client.email && !client.phone && <span className="text-muted">—</span>}
                        </div>
                      </td>
                      <td>{client.ruc_ci || '—'}</td>
                      <td>{getClientTypeBadge(client.client_type)}</td>
                      <td className="text-end">
                        <span className="badge bg-info">{client.total_invoices || 0}</span>
                      </td>
                      <td className="text-end">
                        <strong className="text-success">${(client.total_spent || 0).toFixed(2)}</strong>
                      </td>
                      <td className="text-center">
                        <div className="btn-group btn-group-sm">
                          <button
                            className="btn btn-outline-info"
                            onClick={() => handleViewDetails(client)}
                            title="Ver detalles"
                          >
                            <FaEye />
                          </button>
                          <button
                            className="btn btn-outline-primary"
                            onClick={() => navigate(`/edit-client/${client.id}`)}
                            title="Editar"
                          >
                            <FaEdit />
                          </button>
                          <button
                            className="btn btn-outline-danger"
                            onClick={() => handleDelete(client)}
                            title="Eliminar"
                          >
                            <FaTrash />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        
        {/* Paginación */}
        {!loading && filteredClients.length > 0 && (
          <div className="card-footer bg-white d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div className="text-muted small">
              Mostrando {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, filteredClients.length)} de {filteredClients.length} clientes
            </div>
            <div className="d-flex gap-1">
              <button
                className="btn btn-outline-secondary btn-sm"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(currentPage - 1)}
              >
                Anterior
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
                    className={`btn btn-sm ${currentPage === pageNum ? 'btn-primary' : 'btn-outline-secondary'}`}
                    onClick={() => setCurrentPage(pageNum)}
                  >
                    {pageNum}
                  </button>
                );
              })}
              <button
                className="btn btn-outline-secondary btn-sm"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(currentPage + 1)}
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ClientList;