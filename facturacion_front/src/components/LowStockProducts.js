import React, { useState, useEffect } from 'react';
import { FaFilePdf, FaExclamationTriangle, FaBox, FaSync, FaArrowLeft, FaFilter } from 'react-icons/fa';
import PDFLowStockReport from './PDFLowStockReport';
import api from '../services/api';

const LowStockProducts = ({ onBack }) => {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showPDFModal, setShowPDFModal] = useState(false);
    const [activeFilter, setActiveFilter] = useState('all');

    const handleBack = () => {
        if (onBack) {
            onBack();
        } else {
            window.history.back();
        }
    };

    const fetchLowStockProducts = async () => {
        try {
            setLoading(true);
            setError(null);
            console.log("Buscando productos con bajo stock...");


            // Descomenta esto para usar tu API real:
            const response = await api.get('/products/?low_stock=true');
            setProducts(response.data);
        } catch (error) {
            console.error('Error fetching low stock products:', error);
            setError('Error al cargar los productos con bajo stock');
            setProducts([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLowStockProducts();
    }, []);

    const getStockStatus = (stock, minStock = 3) => {
        if (stock === 0) return { text: 'Agotado', class: 'danger', value: 'outOfStock' };
        if (stock <= minStock) return { text: 'Stock Crítico', class: 'warning', value: 'critical' };
        return { text: 'Bajo Stock', class: 'info', value: 'low' };
    };

    // Filtrar productos según el filtro activo
    const filteredProducts = products.filter(product => {
        const status = getStockStatus(product.stock, product.min_stock);
        
        switch(activeFilter) {
            case 'outOfStock':
                return product.stock === 0;
            case 'critical':
                return product.stock > 0 && product.stock <= (product.min_stock || 3);
            case 'all':
            default:
                return true;
        }
    });

    // Calcular estadísticas
    const criticalStock = products.filter(p => p.stock > 0 && p.stock <= (p.min_stock || 3)).length;
    const outOfStock = products.filter(p => p.stock === 0).length;

    if (loading) {
        return (
            <div className="container-fluid py-4">
                <div className="d-flex justify-content-center align-items-center py-5">
                    <div className="spinner-border text-danger me-3" role="status">
                        <span className="visually-hidden">Cargando...</span>
                    </div>
                    <h4 className="text-muted">Cargando productos con bajo stock...</h4>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container-fluid py-4">
                <div className="alert alert-danger d-flex align-items-center" role="alert">
                    <FaExclamationTriangle className="me-2" />
                    <div>
                        <h5>Error al cargar los datos</h5>
                        <p className="mb-0">{error}</p>
                        <div className="mt-2">
                            <button
                                className="btn btn-sm btn-outline-danger me-2"
                                onClick={fetchLowStockProducts}
                            >
                                <FaSync className="me-1" />
                                Reintentar
                            </button>
                            <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={handleBack}
                            >
                                <FaArrowLeft className="me-1" />
                                Volver
                            </button>
                        </div>
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
                    <div className="d-flex align-items-center mb-2">
                        <h1 className="h3 mb-0 text-danger">
                            <FaExclamationTriangle className="me-2" />
                            Productos con Bajo Stock
                        </h1>
                    </div>
                    <p className="text-muted">
                        Gestiona y genera reportes de productos con stock crítico
                    </p>
                </div>
                <div className="col-md-4 text-end">
                    <div className="d-flex gap-2 justify-content-end">
                        <button 
                            className="btn btn-outline-secondary"
                            onClick={handleBack}
                            title="Volver al inicio"
                        >
                            <FaArrowLeft className="me-1" />
                            Volver
                        </button>
                        
                        <button
                            className="btn btn-outline-secondary"
                            onClick={fetchLowStockProducts}
                            title="Actualizar lista"
                        >
                            <FaSync />
                        </button>
                        
                        <button
                            className="btn btn-danger"
                            onClick={() => setShowPDFModal(true)}
                            disabled={products.length === 0}
                        >
                            <FaFilePdf className="me-2" />
                            Generar PDF
                        </button>
                    </div>
                </div>
            </div>

            {/* Estadísticas rápidas con filtros integrados */}
            <div className="row mb-4">
                <div className="col-md-4">
                    <div 
                        className={`card border-primary ${activeFilter === 'all' ? 'bg-primary bg-opacity-10' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setActiveFilter('all')}
                    >
                        <div className="card-body">
                            <div className="d-flex align-items-center">
                                <div className="flex-grow-1">
                                    <h6 className="text-primary">Total Productos</h6>
                                    <h3 className="mb-0">{products.length}</h3>
                                    {activeFilter === 'all' && (
                                        <small className="text-primary">
                                            <FaFilter className="me-1" />
                                            Filtro activo
                                        </small>
                                    )}
                                </div>
                                <div className="flex-shrink-0">
                                    <FaBox className="text-primary" size={24} />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div 
                        className={`card border-warning ${activeFilter === 'critical' ? 'bg-warning bg-opacity-10' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setActiveFilter('critical')}
                    >
                        <div className="card-body">
                            <div className="d-flex align-items-center">
                                <div className="flex-grow-1">
                                    <h6 className="text-warning">Stock Crítico</h6>
                                    <h3 className="mb-0">{criticalStock}</h3>
                                    {activeFilter === 'critical' && (
                                        <small className="text-warning">
                                            <FaFilter className="me-1" />
                                            Filtro activo
                                        </small>
                                    )}
                                </div>
                                <div className="flex-shrink-0">
                                    <FaExclamationTriangle className="text-warning" size={24} />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div 
                        className={`card border-danger ${activeFilter === 'outOfStock' ? 'bg-danger bg-opacity-10' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setActiveFilter('outOfStock')}
                    >
                        <div className="card-body">
                            <div className="d-flex align-items-center">
                                <div className="flex-grow-1">
                                    <h6 className="text-danger">Agotados</h6>
                                    <h3 className="mb-0">{outOfStock}</h3>
                                    {activeFilter === 'outOfStock' && (
                                        <small className="text-danger">
                                            <FaFilter className="me-1" />
                                            Filtro activo
                                        </small>
                                    )}
                                </div>
                                <div className="flex-shrink-0">
                                    <FaBox className="text-danger" size={24} />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Barra de filtros adicional */}
            <div className="card mb-4">
                <div className="card-body">
                    <div className="d-flex align-items-center justify-content-between">
                        <div className="d-flex align-items-center gap-2">
                            <FaFilter className="text-muted" />
                            <span className="text-muted">Filtros rápidos:</span>
                            <div className="btn-group" role="group">
                                <button
                                    className={`btn btn-sm ${activeFilter === 'all' ? 'btn-primary' : 'btn-outline-primary'}`}
                                    onClick={() => setActiveFilter('all')}
                                >
                                    Todos ({products.length})
                                </button>
                                <button
                                    className={`btn btn-sm ${activeFilter === 'critical' ? 'btn-warning' : 'btn-outline-warning'}`}
                                    onClick={() => setActiveFilter('critical')}
                                >
                                    Stock Crítico ({criticalStock})
                                </button>
                                <button
                                    className={`btn btn-sm ${activeFilter === 'outOfStock' ? 'btn-danger' : 'btn-outline-danger'}`}
                                    onClick={() => setActiveFilter('outOfStock')}
                                >
                                    Agotados ({outOfStock})
                                </button>
                            </div>
                        </div>
                        <div>
                            <span className="badge bg-secondary">
                                Mostrando {filteredProducts.length} de {products.length} productos
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Lista de productos */}
            <div className="card">
                <div className="card-header bg-light d-flex justify-content-between align-items-center">
                    <h5 className="card-title mb-0">Lista de Productos</h5>
                    <span className="badge bg-danger">{filteredProducts.length} productos</span>
                </div>
                <div className="card-body">
                    {filteredProducts.length === 0 ? (
                        <div className="text-center py-5">
                            <FaBox size={64} className="text-muted mb-3" />
                            <h4 className="text-muted">No hay productos</h4>
                            <p className="text-muted">
                                {activeFilter === 'all' 
                                    ? 'No hay productos con bajo stock en este momento.' 
                                    : `No hay productos en la categoría "${activeFilter === 'critical' ? 'Stock Crítico' : 'Agotados'}".`}
                            </p>
                            {activeFilter !== 'all' && (
                                <button
                                    className="btn btn-primary mt-2"
                                    onClick={() => setActiveFilter('all')}
                                >
                                    Ver Todos los Productos
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table table-striped table-hover">
                                <thead className="table-white">
                                    <tr>
                                        <th>#</th>
                                        <th>Producto</th>
                                        <th className="text-center">Stock Actual</th>
                                        <th className="text-center">Stock Mínimo</th>
                                        <th className="text-center">Estado</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredProducts.map((product, index) => {
                                        const status = getStockStatus(product.stock, product.min_stock);
                                        return (
                                            <tr key={product.id} className={status.class === 'danger' ? 'table-danger' : ''}>
                                                <td>{index + 1}</td>
                                                <td>
                                                    <strong>{product.name}</strong>
                                                    {product.code && (
                                                        <div>
                                                            <small className="text-muted">Código: {product.code}</small>
                                                        </div>
                                                    )}
                                                    {product.description && (
                                                        <div>
                                                            <small className="text-muted">{product.description}</small>
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="text-center">
                                                    <span className={`badge bg-${status.class}`}>
                                                        {product.stock} unidades
                                                    </span>
                                                </td>
                                                <td className="text-center">
                                                    {product.min_stock || 3} unidades
                                                </td>
                                                <td className="text-center">
                                                    <span className={`badge bg-${status.class}`}>
                                                        {status.text}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button
                                                        className="btn btn-sm btn-outline-primary"
                                                        onClick={() => {
                                                            alert(`Función de reabastecimiento para ${product.name}`);
                                                        }}
                                                    >
                                                        Reabastecer
                                                    </button>
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

            {/* Modal para PDF Mejorado */}
            {showPDFModal && (
                <PDFLowStockReport
                    lowStockProducts={filteredProducts}
                    activeFilter={activeFilter}
                    onClose={() => setShowPDFModal(false)}
                />
            )}
        </div>
    );
};

export default LowStockProducts;