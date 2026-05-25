import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    FaTools, FaPlus, FaEdit, FaTrash, FaSearch,
    FaBox, FaExclamationTriangle, FaCheckCircle, FaWrench,
    FaEye, FaUserCheck, FaUndo, FaChartBar, FaArrowLeft,
    FaTimes, FaFilter, FaBuilding, FaTag, FaMapMarkerAlt,
    FaInfoCircle, FaCalendarAlt, FaMoneyBillWave, FaBarcode, FaFolderOpen, FaChartLine, FaUser
} from 'react-icons/fa';
import api from '../services/api';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import '../css/activo.css';


/* ─── Componente Principal ─────────────────────────────────────────────── */
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
    const [showFilters, setShowFilters] = useState(false);

    // Filtros
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [categoryFilter, setCategoryFilter] = useState('all');
    const [conditionFilter, setConditionFilter] = useState('all');

    useEffect(() => {
        loadData();
    }, [statusFilter, categoryFilter, conditionFilter]);

    const loadData = async () => {
        setLoading(true);
        try {
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
            toast.error('Error al cargar los datos');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (asset) => {
        const result = await Swal.fire({
            title: '¿Eliminar activo?',
            html: `¿Estás seguro de eliminar <strong>${asset.name}</strong>?<br/>
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
                await api.delete(`assets/${asset.id}/`);
                toast.success('Activo eliminado exitosamente');
                loadData();
            } catch (error) {
                console.error('Error deleting asset:', error);
                toast.error('Error al eliminar el activo');
            }
        }
    };

    const handleAssign = async () => {
        if (!assignTo.trim()) {
            toast.error('Ingresa el nombre de la persona');
            return;
        }

        try {
            await api.post(`assets/${selectedAsset.id}/assign/`, {
                assigned_to: assignTo
            });
            toast.success('Activo asignado exitosamente');
            setShowAssignModal(false);
            setAssignTo('');
            loadData();
        } catch (error) {
            console.error('Error assigning asset:', error);
            toast.error('Error al asignar el activo');
        }
    };

    const handleReturn = async (asset) => {
        const result = await Swal.fire({
            title: '¿Devolver activo?',
            text: `¿Confirmas la devolución de ${asset.name}?`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#f59e0b',
            confirmButtonText: 'Sí, devolver',
            cancelButtonText: 'Cancelar'
        });

        if (result.isConfirmed) {
            try {
                await api.post(`assets/${asset.id}/return_asset/`);
                toast.success('Activo devuelto exitosamente');
                loadData();
            } catch (error) {
                console.error('Error returning asset:', error);
                toast.error('Error al devolver el activo');
            }
        }
    };

    const handleCancel = () => {
        navigate('/home');
    };

    const resetFilters = () => {
        setSearchTerm('');
        setStatusFilter('all');
        setCategoryFilter('all');
        setConditionFilter('all');
    };

    // Filtrar activos por búsqueda
    const filteredAssets = assets.filter(asset => {
        const matchesSearch = searchTerm === '' ||
            asset.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.brand?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.model?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            asset.serial_number?.toLowerCase().includes(searchTerm.toLowerCase());

        return matchesSearch;
    });

    const getStatusConfig = (status) => {
        const configs = {
            available: { class: 'status-available', icon: FaCheckCircle, text: 'Disponible' },
            in_use: { class: 'status-in_use', icon: FaUserCheck, text: 'En Uso' },
            maintenance: { class: 'status-maintenance', icon: FaWrench, text: 'Mantenimiento' },
            damaged: { class: 'status-damaged', icon: FaExclamationTriangle, text: 'Dañado' },
            retired: { class: 'status-retired', icon: FaBox, text: 'Dado de Baja' }
        };
        return configs[status] || configs.available;
    };

    const getConditionConfig = (condition) => {
        const configs = {
            excellent: { class: 'condition-excellent', text: 'Excelente' },
            good: { class: 'condition-good', text: 'Bueno' },
            fair: { class: 'condition-fair', text: 'Regular' },
            poor: { class: 'condition-poor', text: 'Malo' }
        };
        return configs[condition] || configs.good;
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        return new Date(dateStr).toLocaleDateString('es-ES');
    };

    const formatMoney = (value) => {
        if (!value) return 'N/A';
        return `$${parseFloat(value).toFixed(2)}`;
    };

    const hasActiveFilters = searchTerm !== '' || 
                             statusFilter !== 'all' || 
                             categoryFilter !== 'all' || 
                             conditionFilter !== 'all';

    if (loading) {
        return (
            <div className="al-root">
                <div className="al-loading">
                    <div className="al-spinner" />
                    <span style={{ color: 'var(--text-muted)' }}>Cargando activos...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="al-root">
            <Toaster position="top-right" />

            {/* Header */}
            <header className="al-header">
                <button className="al-btn al-btn-secondary al-btn-sm" onClick={handleCancel}>
                    <FaArrowLeft size={12} /> Volver
                </button>

                <div className="al-header-title">
                    <FaTools size={14} style={{ color: 'var(--primary)' }} />
                    Gestión de Activos y Herramientas
                    <span className="al-badge">{assets.length}</span>
                </div>

                <div className="al-header-actions">
                    <button 
                        className="al-btn al-btn-secondary al-btn-sm"
                        onClick={() => setShowFilters(!showFilters)}
                    >
                        <FaFilter size={11} /> Filtros
                        {hasActiveFilters && (
                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)', display: 'inline-block' }} />
                        )}
                    </button>
                    <button 
                        className="al-btn al-btn-primary al-btn-sm"
                        onClick={() => navigate('/assetsForm')}
                    >
                        <FaPlus size={11} /> Nuevo Activo
                    </button>
                </div>
            </header>

            <div className="al-body">
                {/* Estadísticas */}
                {statistics && (
                    <div className="al-stats">
                        <div className="al-stat-card primary">
                            <div className="al-stat-content">
                                <div className="al-stat-info">
                                    <h6>Total Activos</h6>
                                    <h2 className="primary">{statistics.total}</h2>
                                </div>
                                <FaTools className="al-stat-icon" />
                            </div>
                        </div>
                        <div className="al-stat-card success">
                            <div className="al-stat-content">
                                <div className="al-stat-info">
                                    <h6>Disponibles</h6>
                                    <h2 className="success">
                                        {statistics.by_status?.find(s => s.status === 'available')?.count || 0}
                                    </h2>
                                </div>
                                <FaCheckCircle className="al-stat-icon" />
                            </div>
                        </div>
                        <div className="al-stat-card info">
                            <div className="al-stat-content">
                                <div className="al-stat-info">
                                    <h6>En Uso</h6>
                                    <h2 className="info">
                                        {statistics.by_status?.find(s => s.status === 'in_use')?.count || 0}
                                    </h2>
                                </div>
                                <FaUserCheck className="al-stat-icon" />
                            </div>
                        </div>
                        <div className="al-stat-card warning">
                            <div className="al-stat-content">
                                <div className="al-stat-info">
                                    <h6>Necesitan Mantenimiento</h6>
                                    <h2 className="warning">{statistics.needs_maintenance || 0}</h2>
                                </div>
                                <FaWrench className="al-stat-icon" />
                            </div>
                        </div>
                    </div>
                )}

                {/* Panel de Filtros */}
                {showFilters && (
                    <div className="al-filter-card">
                        <div className="al-filter-header">
                            <div className="al-filter-title">
                                <FaFilter size={11} /> Filtros avanzados
                                {hasActiveFilters && (
                                    <span className="al-badge" style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
                                        activos
                                    </span>
                                )}
                            </div>
                            {hasActiveFilters && (
                                <button className="al-clear-btn" onClick={resetFilters}>
                                    <FaTimes size={10} /> Limpiar todo
                                </button>
                            )}
                        </div>
                        <div className="al-filter-body">
                            <div className="al-search-wrapper">
                                <FaSearch className="al-search-icon" />
                                <input
                                    type="text"
                                    className="al-search-input"
                                    placeholder="Buscar por nombre, código, marca..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>

                            <select
                                className="al-select"
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                            >
                                <option value="all">Todos los estados</option>
                                <option value="available">✅ Disponible</option>
                                <option value="in_use">👤 En Uso</option>
                                <option value="maintenance">🔧 Mantenimiento</option>
                                <option value="damaged">⚠️ Dañado</option>
                                <option value="retired">📦 Dado de Baja</option>
                            </select>

                            <select
                                className="al-select"
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

                            <select
                                className="al-select"
                                value={conditionFilter}
                                onChange={(e) => setConditionFilter(e.target.value)}
                            >
                                <option value="all">Todas las condiciones</option>
                                <option value="excellent">🌟 Excelente</option>
                                <option value="good">👍 Bueno</option>
                                <option value="fair">👌 Regular</option>
                                <option value="poor">👎 Malo</option>
                            </select>
                        </div>
                    </div>
                )}

                {/* Filtros rápidos cuando el panel está cerrado */}
                {!showFilters && (
                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                        <button
                            className={`al-clear-btn ${statusFilter === 'all' ? 'al-btn-primary' : ''}`}
                            style={statusFilter === 'all' ? { background: 'var(--primary)', color: 'white' } : {}}
                            onClick={() => setStatusFilter('all')}
                        >
                            Todos
                        </button>
                        <button
                            className="al-clear-btn"
                            onClick={() => setStatusFilter('available')}
                        >
                            ✅ Disponibles
                        </button>
                        <button
                            className="al-clear-btn"
                            onClick={() => setStatusFilter('in_use')}
                        >
                            👤 En Uso
                        </button>
                        <button
                            className="al-clear-btn"
                            onClick={() => setStatusFilter('maintenance')}
                        >
                            🔧 Mantenimiento
                        </button>
                    </div>
                )}

                {/* Tabla de activos */}
                <div className="al-table-card">
                    <div className="al-table-header">
                        <div className="al-table-title">
                            <FaBox size={12} /> Listado de Activos
                            <span className="al-badge">{filteredAssets.length} resultados</span>
                        </div>
                        {filteredAssets.length > 0 && (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)' }}>
                                Mostrando {filteredAssets.length} de {assets.length}
                            </span>
                        )}
                    </div>

                    <div className="al-table-wrapper">
                        <table className="al-table">
                            <thead>
                                <tr>
                                    <th>Código</th>
                                    <th>Nombre</th>
                                    <th>Categoría</th>
                                    <th>Marca/Modelo</th>
                                    <th className="text-center">Estado</th>
                                    <th className="text-center">Condición</th>
                                    <th>Ubicación</th>
                                    <th className="text-center">Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredAssets.length === 0 ? (
                                    <tr>
                                        <td colSpan="8">
                                            <div className="al-empty">
                                                <FaBox size={48} />
                                                <p>
                                                    {hasActiveFilters
                                                        ? "No hay resultados con los filtros actuales"
                                                        : "No hay activos registrados"}
                                                </p>
                                                {hasActiveFilters && (
                                                    <button className="al-clear-btn" onClick={resetFilters}>
                                                        Limpiar filtros
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    filteredAssets.map(asset => {
                                        const statusConfig = getStatusConfig(asset.status);
                                        const StatusIcon = statusConfig.icon;
                                        const conditionConfig = getConditionConfig(asset.condition);

                                        return (
                                            <tr key={asset.id}>
                                                <td>
                                                    <code className="al-info-value mono" style={{ color: 'var(--primary)', fontWeight: 600 }}>
                                                        {asset.code}
                                                    </code>
                                                </td>
                                                <td>
                                                    <div style={{ fontWeight: 600 }}>{asset.name}</div>
                                                    {asset.assigned_to && (
                                                        <small style={{ color: 'var(--text-faint)' }}>
                                                            <FaUserCheck size={10} style={{ marginRight: '0.25rem' }} />
                                                            {asset.assigned_to}
                                                        </small>
                                                    )}
                                                </td>
                                                <td>
                                                    <span className="al-badge">
                                                        {asset.category_name || 'Sin categoría'}
                                                    </span>
                                                </td>
                                                <td>
                                                    {asset.brand && (
                                                        <>
                                                            <div style={{ fontSize: '0.8125rem' }}>{asset.brand}</div>
                                                            {asset.model && (
                                                                <small style={{ color: 'var(--text-faint)' }}>{asset.model}</small>
                                                            )}
                                                        </>
                                                    )}
                                                </td>
                                                <td className="text-center">
                                                    <span className={`al-status-badge ${statusConfig.class}`}>
                                                        <StatusIcon size={10} />
                                                        {statusConfig.text}
                                                    </span>
                                                </td>
                                                <td className="text-center">
                                                    <span className={`al-status-badge ${conditionConfig.class}`}>
                                                        {conditionConfig.text}
                                                    </span>
                                                </td>
                                                <td>
                                                    <small>{asset.location || 'No especificada'}</small>
                                                </td>
                                                <td className="text-center">
                                                    <div className="al-actions">
                                                        <button
                                                            className="al-action-btn btn-view"
                                                            onClick={() => {
                                                                setSelectedAsset(asset);
                                                                setShowDetailModal(true);
                                                            }}
                                                            title="Ver detalles"
                                                        >
                                                            <FaEye size={12} />
                                                        </button>
                                                        <button
                                                            className="al-action-btn btn-edit"
                                                            onClick={() => navigate(`/assets/edit/${asset.id}`)}
                                                            title="Editar"
                                                        >
                                                            <FaEdit size={12} />
                                                        </button>
                                                        {asset.status === 'available' && (
                                                            <button
                                                                className="al-action-btn btn-assign"
                                                                onClick={() => {
                                                                    setSelectedAsset(asset);
                                                                    setShowAssignModal(true);
                                                                }}
                                                                title="Asignar"
                                                            >
                                                                <FaUserCheck size={12} />
                                                            </button>
                                                        )}
                                                        {asset.status === 'in_use' && asset.assigned_to && (
                                                            <button
                                                                className="al-action-btn btn-return"
                                                                onClick={() => handleReturn(asset)}
                                                                title="Devolver"
                                                            >
                                                                <FaUndo size={12} />
                                                            </button>
                                                        )}
                                                        <button
                                                            className="al-action-btn btn-delete"
                                                            onClick={() => handleDelete(asset)}
                                                            title="Eliminar"
                                                        >
                                                            <FaTrash size={12} />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Modal de Detalles */}
            {showDetailModal && selectedAsset && (
                <div className="al-modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowDetailModal(false)}>
                    <div className="al-modal">
                        <div className="al-modal-header primary">
                            <h5 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <FaEye size={16} /> Detalles del Activo
                            </h5>
                            <button 
                                onClick={() => setShowDetailModal(false)}
                                style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.25rem' }}
                            >
                                ×
                            </button>
                        </div>
                        <div className="al-modal-body">
                            <div className="al-info-grid">
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaBarcode size={10} /> Código</div>
                                    <div className="al-info-value mono">{selectedAsset.code}</div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaTag size={10} /> Nombre</div>
                                    <div className="al-info-value">{selectedAsset.name}</div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaFolderOpen size={10} /> Categoría</div>
                                    <div className="al-info-value">{selectedAsset.category_name || 'N/A'}</div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaMapMarkerAlt size={10} /> Ubicación</div>
                                    <div className="al-info-value">{selectedAsset.location || 'N/A'}</div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaBuilding size={10} /> Marca</div>
                                    <div className="al-info-value">{selectedAsset.brand || 'N/A'}</div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaTag size={10} /> Modelo</div>
                                    <div className="al-info-value">{selectedAsset.model || 'N/A'}</div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaBarcode size={10} /> Número de Serie</div>
                                    <div className="al-info-value mono">{selectedAsset.serial_number || 'N/A'}</div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaChartLine size={10} /> Estado</div>
                                    <div className="al-info-value">
                                        <span className={`al-status-badge ${getStatusConfig(selectedAsset.status).class}`}>
                                            {getStatusConfig(selectedAsset.status).text}
                                        </span>
                                    </div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaCheckCircle size={10} /> Condición</div>
                                    <div className="al-info-value">
                                        <span className={`al-status-badge ${getConditionConfig(selectedAsset.condition).class}`}>
                                            {getConditionConfig(selectedAsset.condition).text}
                                        </span>
                                    </div>
                                </div>
                                <div className="al-info-item">
                                    <div className="al-info-label"><FaUserCheck size={10} /> Asignado a</div>
                                    <div className="al-info-value">{selectedAsset.assigned_to || 'No asignado'}</div>
                                </div>
                                {selectedAsset.purchase_price && (
                                    <div className="al-info-item">
                                        <div className="al-info-label"><FaMoneyBillWave size={10} /> Precio de Compra</div>
                                        <div className="al-info-value">{formatMoney(selectedAsset.purchase_price)}</div>
                                    </div>
                                )}
                                {selectedAsset.purchase_date && (
                                    <div className="al-info-item">
                                        <div className="al-info-label"><FaCalendarAlt size={10} /> Fecha de Compra</div>
                                        <div className="al-info-value">{formatDate(selectedAsset.purchase_date)}</div>
                                    </div>
                                )}
                                {selectedAsset.description && (
                                    <div className="al-info-item al-full-width">
                                        <div className="al-info-label"><FaInfoCircle size={10} /> Descripción</div>
                                        <div className="al-info-value">{selectedAsset.description}</div>
                                    </div>
                                )}
                                {selectedAsset.notes && (
                                    <div className="al-info-item al-full-width">
                                        <div className="al-info-label"><FaInfoCircle size={10} /> Notas</div>
                                        <div className="al-info-value">{selectedAsset.notes}</div>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="al-modal-footer">
                            <button className="al-btn al-btn-secondary" onClick={() => setShowDetailModal(false)}>
                                Cerrar
                            </button>
                            <button 
                                className="al-btn al-btn-primary"
                                onClick={() => {
                                    setShowDetailModal(false);
                                    navigate(`/assets/edit/${selectedAsset.id}`);
                                }}
                            >
                                <FaEdit size={12} /> Editar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de Asignación */}
            {showAssignModal && selectedAsset && (
                <div className="al-modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowAssignModal(false)}>
                    <div className="al-modal" style={{ maxWidth: '450px' }}>
                        <div className="al-modal-header success">
                            <h5 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <FaUserCheck size={16} /> Asignar Activo
                            </h5>
                            <button 
                                onClick={() => {
                                    setShowAssignModal(false);
                                    setAssignTo('');
                                }}
                                style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.25rem' }}
                            >
                                ×
                            </button>
                        </div>
                        <div className="al-modal-body">
                            <div style={{ marginBottom: '1rem', padding: '0.5rem', background: 'var(--surface-hover)', borderRadius: 'var(--radius-sm)' }}>
                                <strong>Activo:</strong> {selectedAsset.code} - {selectedAsset.name}
                            </div>
                            <div className="al-form-group">
                                <label className="al-label">
                                    <FaUser size={12} /> Asignar a:
                                </label>
                                <input
                                    type="text"
                                    className="al-search-input"
                                    value={assignTo}
                                    onChange={(e) => setAssignTo(e.target.value)}
                                    placeholder="Nombre de la persona responsable"
                                    autoFocus
                                />
                            </div>
                        </div>
                        <div className="al-modal-footer">
                            <button 
                                className="al-btn al-btn-secondary"
                                onClick={() => {
                                    setShowAssignModal(false);
                                    setAssignTo('');
                                }}
                            >
                                Cancelar
                            </button>
                            <button 
                                className="al-btn al-btn-primary"
                                onClick={handleAssign}
                                style={{ background: 'var(--success)' }}
                            >
                                <FaUserCheck size={12} /> Asignar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AssetsList;