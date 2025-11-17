import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    FaTools, FaPlus, FaEdit, FaTrash, FaSearch,
    FaBox, FaExclamationTriangle, FaCheckCircle, FaWrench,
    FaEye, FaUserCheck, FaUndo, FaChartBar
} from 'react-icons/fa';
import api from '../services/api';
import { showSuccessAlert, showGenericAlert } from '../herpert';

const AssetsList = () => {
    const navigate = useNavigate();
    const [assets, setAssets] = useState([]);
    const [categories, setCategories] = useState([]);
    const [statistics, setStatistics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [showAssignModal, setShowAssignModal] = useState(false);
    const [assignTo, setAssignTo] = useState('');

    // Filtros
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [categoryFilter, setCategoryFilter] = useState('all');
    const [conditionFilter, setConditionFilter] = useState('all');

    useEffect(() => {
        loadData();
    }, [statusFilter, categoryFilter, conditionFilter]);

    const handleCancel = () => {
        navigate('/home');
    };


    const loadData = async () => {
        setLoading(true);
        try {
            // Construir parámetros de filtro
            const params = {};
            if (statusFilter !== 'all') params.status = statusFilter;
            if (categoryFilter !== 'all') params.category = categoryFilter;
            if (conditionFilter !== 'all') params.condition = conditionFilter;

            const [assetsData, categoriesData, statsData] = await Promise.all([
                api.get('assets/', { params }),
                api.get('assets/categories/'),
                api.get('assets/statistics/')
            ]);

            setAssets(assetsData.data);
            setCategories(categoriesData.data);
            setStatistics(statsData.data);
        } catch (error) {
            console.error('Error loading data:', error);
            showGenericAlert('Error al cargar los datos');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id) => {
        if (window.confirm('¿Estás seguro de eliminar este activo?')) {
            try {
                await api.delete(`assets/${id}/`);
                showSuccessAlert('Activo eliminado exitosamente');
                loadData();
            } catch (error) {
                console.error('Error deleting asset:', error);
                showGenericAlert('Error al eliminar el activo');
            }
        }
    };

    const handleAssign = async () => {
        if (!assignTo.trim()) {
            showGenericAlert('Ingresa el nombre de la persona');
            return;
        }

        try {
            await api.post(`assets/${selectedAsset.id}/assign/`, {
                assigned_to: assignTo
            });
            showSuccessAlert('Activo asignado exitosamente');
            setShowAssignModal(false);
            setAssignTo('');
            loadData();
        } catch (error) {
            console.error('Error assigning asset:', error);
            showGenericAlert('Error al asignar el activo');
        }
    };

    const handleReturn = async (assetId) => {
        if (window.confirm('¿Confirmas la devolución de este activo?')) {
            try {
                await api.post(`assets/${assetId}/return_asset/`);
                showSuccessAlert('Activo devuelto exitosamente');
                loadData();
            } catch (error) {
                console.error('Error returning asset:', error);
                showGenericAlert('Error al devolver el activo');
            }
        }
    };

    // Filtrar activos por búsqueda
    const filteredAssets = assets.filter(asset => {
        const matchesSearch =
            asset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.brand?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.model?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.serial_number?.toLowerCase().includes(searchTerm.toLowerCase());

        return matchesSearch;
    });

    const getStatusBadge = (status) => {
        const badges = {
            available: { color: 'success', icon: FaCheckCircle, text: 'Disponible' },
            in_use: { color: 'primary', icon: FaUserCheck, text: 'En Uso' },
            maintenance: { color: 'warning', icon: FaWrench, text: 'Mantenimiento' },
            damaged: { color: 'danger', icon: FaExclamationTriangle, text: 'Dañado' },
            retired: { color: 'secondary', icon: FaBox, text: 'Dado de Baja' }
        };
        return badges[status] || badges.available;
    };

    const getConditionBadge = (condition) => {
        const colors = {
            excellent: 'success',
            good: 'info',
            fair: 'warning',
            poor: 'danger'
        };
        const labels = {
            excellent: 'Excelente',
            good: 'Bueno',
            fair: 'Regular',
            poor: 'Malo'
        };
        return { color: colors[condition] || 'secondary', label: labels[condition] || condition };
    };

    if (loading) {
        return (
            <div className="container-fluid py-5">
                <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
                    <div className="text-center">
                        <div className="spinner-border text-primary mb-3" style={{ width: '3rem', height: '3rem' }}></div>
                        <h4 className="text-muted">Cargando activos...</h4>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="container-fluid py-4">
            {/* Header */}
            <div className="row mb-4">
                <div className="col-md-8">
                    <h1 className="h3 mb-2">
                        <FaTools className="me-2 text-primary" />
                        Gestión de Activos y Herramientas
                    </h1>
                    <p className="text-muted">Administra todas las herramientas y equipos del negocio</p>
                </div>
                <div className="col-md-4 text-end">
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleCancel}
                        disabled={loading}
                    >
                        ❌ Cancelar
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={() => navigate('/assetsForm')}
                    >
                        <FaPlus className="me-2" />
                        Nuevo Activo
                    </button>
                </div>
            </div>

            {/* Estadísticas */}
            {statistics && (
                <div className="row mb-4">
                    <div className="col-md-3">
                        <div className="card bg-primary text-white">
                            <div className="card-body">
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 className="card-subtitle mb-2">Total Activos</h6>
                                        <h2 className="card-title mb-0">{statistics.total}</h2>
                                    </div>
                                    <FaTools size={40} className="opacity-50" />
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-md-3">
                        <div className="card bg-success text-white">
                            <div className="card-body">
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 className="card-subtitle mb-2">Disponibles</h6>
                                        <h2 className="card-title mb-0">
                                            {statistics.by_status.find(s => s.status === 'available')?.count || 0}
                                        </h2>
                                    </div>
                                    <FaCheckCircle size={40} className="opacity-50" />
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-md-3">
                        <div className="card bg-info text-white">
                            <div className="card-body">
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 className="card-subtitle mb-2">En Uso</h6>
                                        <h2 className="card-title mb-0">
                                            {statistics.by_status.find(s => s.status === 'in_use')?.count || 0}
                                        </h2>
                                    </div>
                                    <FaUserCheck size={40} className="opacity-50" />
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-md-3">
                        <div className="card bg-warning text-dark">
                            <div className="card-body">
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 className="card-subtitle mb-2">Necesitan Mantenimiento</h6>
                                        <h2 className="card-title mb-0">{statistics.needs_maintenance}</h2>
                                    </div>
                                    <FaWrench size={40} className="opacity-50" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Filtros y búsqueda */}
            <div className="card mb-4">
                <div className="card-body">
                    <div className="row g-3">
                        <div className="col-md-4">
                            <div className="input-group">
                                <span className="input-group-text">
                                    <FaSearch />
                                </span>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="Buscar por nombre, código, marca..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="col-md-2">
                            <select
                                className="form-select"
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                            >
                                <option value="all">Todos los estados</option>
                                <option value="available">Disponible</option>
                                <option value="in_use">En Uso</option>
                                <option value="maintenance">Mantenimiento</option>
                                <option value="damaged">Dañado</option>
                                <option value="retired">Dado de Baja</option>
                            </select>
                        </div>

                        <div className="col-md-3">
                            <select
                                className="form-select"
                                value={categoryFilter}
                                onChange={(e) => setCategoryFilter(e.target.value)}
                            >
                                <option value="all">Todas las categorías</option>
                                {categories.map(cat => (
                                    <option key={cat.id} value={cat.id}>
                                        {cat.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="col-md-3">
                            <select
                                className="form-select"
                                value={conditionFilter}
                                onChange={(e) => setConditionFilter(e.target.value)}
                            >
                                <option value="all">Todas las condiciones</option>
                                <option value="excellent">Excelente</option>
                                <option value="good">Bueno</option>
                                <option value="fair">Regular</option>
                                <option value="poor">Malo</option>
                            </select>
                        </div>
                    </div>

                    {(searchTerm || statusFilter !== 'all' || categoryFilter !== 'all' || conditionFilter !== 'all') && (
                        <div className="mt-3">
                            <span className="badge bg-secondary me-2">
                                Mostrando {filteredAssets.length} de {assets.length} activos
                            </span>
                            <button
                                className="btn btn-sm btn-link text-decoration-none"
                                onClick={() => {
                                    setSearchTerm('');
                                    setStatusFilter('all');
                                    setCategoryFilter('all');
                                    setConditionFilter('all');
                                }}
                            >
                                Limpiar filtros
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Tabla de activos */}
            <div className="card">
                <div className="card-header bg-light">
                    <h5 className="card-title mb-0">Listado de Activos</h5>
                </div>
                <div className="card-body p-0">
                    {filteredAssets.length === 0 ? (
                        <div className="text-center py-5">
                            <FaBox size={64} className="text-muted mb-3" />
                            <h4 className="text-muted">No se encontraron activos</h4>
                            <p className="text-muted">
                                {searchTerm || statusFilter !== 'all' || categoryFilter !== 'all'
                                    ? 'Intenta ajustar los filtros de búsqueda'
                                    : 'Comienza agregando tu primer activo'}
                            </p>
                            {!searchTerm && statusFilter === 'all' && categoryFilter === 'all' && (
                                <button
                                    className="btn btn-primary mt-3"
                                    onClick={() => navigate('/assets/new')}
                                >
                                    <FaPlus className="me-2" />
                                    Agregar Primer Activo
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table table-hover table-striped mb-0">
                                <thead className="table-primary">
                                    <tr>
                                        <th style={{ width: '10%' }}>Código</th>
                                        <th style={{ width: '20%' }}>Nombre</th>
                                        <th style={{ width: '12%' }}>Categoría</th>
                                        <th style={{ width: '12%' }}>Marca/Modelo</th>
                                        <th style={{ width: '10%' }} className="text-center">Estado</th>
                                        <th style={{ width: '10%' }} className="text-center">Condición</th>
                                        <th style={{ width: '13%' }}>Ubicación</th>
                                        <th style={{ width: '13%' }} className="text-center">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredAssets.map(asset => {
                                        const statusBadge = getStatusBadge(asset.status);
                                        const StatusIcon = statusBadge.icon;
                                        const conditionBadge = getConditionBadge(asset.condition);

                                        return (
                                            <tr key={asset.id}>
                                                <td>
                                                    <code className="text-primary fw-bold">{asset.code}</code>
                                                </td>
                                                <td>
                                                    <div className="fw-bold">{asset.name}</div>
                                                    {asset.assigned_to && (
                                                        <small className="text-muted">
                                                            <FaUserCheck className="me-1" />
                                                            {asset.assigned_to}
                                                        </small>
                                                    )}
                                                </td>
                                                <td>
                                                    <span className="badge bg-light text-dark border">
                                                        {asset.category_name || 'Sin categoría'}
                                                    </span>
                                                </td>
                                                <td>
                                                    {asset.brand && (
                                                        <div>
                                                            <small className="d-block">{asset.brand}</small>
                                                            {asset.model && (
                                                                <small className="text-muted">{asset.model}</small>
                                                            )}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="text-center">
                                                    <span className={`badge bg-${statusBadge.color}`}>
                                                        <StatusIcon className="me-1" size={12} />
                                                        {statusBadge.text}
                                                    </span>
                                                </td>
                                                <td className="text-center">
                                                    <span className={`badge bg-${conditionBadge.color}`}>
                                                        {conditionBadge.label}
                                                    </span>
                                                </td>
                                                <td>
                                                    <small>{asset.location || 'No especificada'}</small>
                                                </td>
                                                <td className="text-center">
                                                    <div className="btn-group btn-group-sm">
                                                        <button
                                                            className="btn btn-outline-info"
                                                            onClick={() => {
                                                                setSelectedAsset(asset);
                                                                setShowDetailModal(true);
                                                            }}
                                                            title="Ver detalles"
                                                        >
                                                            <FaEye />
                                                        </button>
                                                        <button
                                                            className="btn btn-outline-secondary"
                                                            onClick={() => navigate(`/assets/edit/${asset.id}`)}
                                                            title="Editar"
                                                        >
                                                            <FaEdit />
                                                        </button>
                                                        {asset.status === 'available' && (
                                                            <button
                                                                className="btn btn-outline-success"
                                                                onClick={() => {
                                                                    setSelectedAsset(asset);
                                                                    setShowAssignModal(true);
                                                                }}
                                                                title="Asignar"
                                                            >
                                                                <FaUserCheck />
                                                            </button>
                                                        )}
                                                        {asset.status === 'in_use' && asset.assigned_to && (
                                                            <button
                                                                className="btn btn-outline-warning"
                                                                onClick={() => handleReturn(asset.id)}
                                                                title="Devolver"
                                                            >
                                                                <FaUndo />
                                                            </button>
                                                        )}
                                                        <button
                                                            className="btn btn-outline-danger"
                                                            onClick={() => handleDelete(asset.id)}
                                                            title="Eliminar"
                                                        >
                                                            <FaTrash />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* Modal de Detalles */}
            {showDetailModal && selectedAsset && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-lg">
                        <div className="modal-content">
                            <div className="modal-header bg-primary text-white">
                                <h5 className="modal-title">
                                    <FaEye className="me-2" />
                                    Detalles del Activo
                                </h5>
                                <button
                                    className="btn-close btn-close-white"
                                    onClick={() => setShowDetailModal(false)}
                                ></button>
                            </div>
                            <div className="modal-body">
                                <div className="row">
                                    <div className="col-md-6 mb-3">
                                        <strong>Código:</strong>
                                        <p className="mb-0">{selectedAsset.code}</p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Nombre:</strong>
                                        <p className="mb-0">{selectedAsset.name}</p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Categoría:</strong>
                                        <p className="mb-0">{selectedAsset.category_name || 'N/A'}</p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Ubicación:</strong>
                                        <p className="mb-0">{selectedAsset.location || 'N/A'}</p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Marca:</strong>
                                        <p className="mb-0">{selectedAsset.brand || 'N/A'}</p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Modelo:</strong>
                                        <p className="mb-0">{selectedAsset.model || 'N/A'}</p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Número de Serie:</strong>
                                        <p className="mb-0">{selectedAsset.serial_number || 'N/A'}</p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Estado:</strong>
                                        <p className="mb-0">
                                            <span className={`badge bg-${getStatusBadge(selectedAsset.status).color}`}>
                                                {getStatusBadge(selectedAsset.status).text}
                                            </span>
                                        </p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Condición:</strong>
                                        <p className="mb-0">
                                            <span className={`badge bg-${getConditionBadge(selectedAsset.condition).color}`}>
                                                {getConditionBadge(selectedAsset.condition).label}
                                            </span>
                                        </p>
                                    </div>
                                    <div className="col-md-6 mb-3">
                                        <strong>Asignado a:</strong>
                                        <p className="mb-0">{selectedAsset.assigned_to || 'No asignado'}</p>
                                    </div>
                                    {selectedAsset.purchase_price && (
                                        <div className="col-md-6 mb-3">
                                            <strong>Precio de Compra:</strong>
                                            <p className="mb-0">${selectedAsset.purchase_price}</p>
                                        </div>
                                    )}
                                    {selectedAsset.purchase_date && (
                                        <div className="col-md-6 mb-3">
                                            <strong>Fecha de Compra:</strong>
                                            <p className="mb-0">{new Date(selectedAsset.purchase_date).toLocaleDateString()}</p>
                                        </div>
                                    )}
                                    {selectedAsset.description && (
                                        <div className="col-12 mb-3">
                                            <strong>Descripción:</strong>
                                            <p className="mb-0">{selectedAsset.description}</p>
                                        </div>
                                    )}
                                    {selectedAsset.notes && (
                                        <div className="col-12 mb-3">
                                            <strong>Notas:</strong>
                                            <p className="mb-0">{selectedAsset.notes}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => setShowDetailModal(false)}
                                >
                                    Cerrar
                                </button>
                                <button
                                    className="btn btn-primary"
                                    onClick={() => {
                                        setShowDetailModal(false);
                                        navigate(`/assets/edit/${selectedAsset.id}`);
                                    }}
                                >
                                    <FaEdit className="me-2" />
                                    Editar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de Asignación */}
            {showAssignModal && selectedAsset && (
                <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog">
                        <div className="modal-content">
                            <div className="modal-header bg-success text-white">
                                <h5 className="modal-title">
                                    <FaUserCheck className="me-2" />
                                    Asignar Activo
                                </h5>
                                <button
                                    className="btn-close btn-close-white"
                                    onClick={() => {
                                        setShowAssignModal(false);
                                        setAssignTo('');
                                    }}
                                ></button>
                            </div>
                            <div className="modal-body">
                                <p><strong>Activo:</strong> {selectedAsset.code} - {selectedAsset.name}</p>
                                <div className="mb-3">
                                    <label className="form-label">Asignar a:</label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={assignTo}
                                        onChange={(e) => setAssignTo(e.target.value)}
                                        placeholder="Nombre de la persona"
                                        autoFocus
                                    />
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => {
                                        setShowAssignModal(false);
                                        setAssignTo('');
                                    }}
                                >
                                    Cancelar
                                </button>
                                <button
                                    className="btn btn-success"
                                    onClick={handleAssign}
                                >
                                    <FaUserCheck className="me-2" />
                                    Asignar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AssetsList;