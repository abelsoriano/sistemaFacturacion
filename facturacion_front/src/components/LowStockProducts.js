import React, { useState, useEffect } from 'react';
import { FaFilePdf, FaExclamationTriangle, FaBox, FaSync, FaArrowLeft } from 'react-icons/fa';
import api from '../services/api';
import PDFLowStockReport from './PDFLowStockReport';

const LowStockProducts = ({ onBack }) => {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showPDFModal, setShowPDFModal] = useState(false);

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

            const response = await api.get('/products/?low_stock=true');
            console.log("Respuesta recibida:", response.data);

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
        if (stock === 0) return { text: 'Agotado', class: 'danger' };
        if (stock <= minStock) return { text: 'Stock Crítico', class: 'warning' };
        return { text: 'Bajo Stock', class: 'info' };
    };

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

            {/* Estadísticas rápidas */}
            <div className="row mb-4">
                <div className="col-md-4">
                    <div className="card border-primary">
                        <div className="card-body">
                            <div className="d-flex align-items-center">
                                <div className="flex-grow-1">
                                    <h6 className="text-primary">Total Productos con Bajo Stock</h6>
                                    <h3 className="mb-0">{products.length}</h3>
                                </div>
                                <div className="flex-shrink-0">
                                    <FaBox className="text-primary" size={24} />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div className="card border-warning">
                        <div className="card-body">
                            <div className="d-flex align-items-center">
                                <div className="flex-grow-1">
                                    <h6 className="text-warning">Stock Crítico</h6>
                                    <h3 className="mb-0">{criticalStock}</h3>
                                </div>
                                <div className="flex-shrink-0">
                                    <FaExclamationTriangle className="text-warning" size={24} />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div className="card border-danger">
                        <div className="card-body">
                            <div className="d-flex align-items-center">
                                <div className="flex-grow-1">
                                    <h6 className="text-danger">Agotados</h6>
                                    <h3 className="mb-0">{outOfStock}</h3>
                                </div>
                                <div className="flex-shrink-0">
                                    <FaBox className="text-danger" size={24} />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Lista de productos */}
            <div className="card">
                <div className="card-header bg-light d-flex justify-content-between align-items-center">
                    <h5 className="card-title mb-0">Lista de Productos con Bajo Stock</h5>
                    <span className="badge bg-danger">{products.length} productos</span>
                </div>
                <div className="card-body">
                    {products.length === 0 ? (
                        <div className="text-center py-5">
                            <FaBox size={64} className="text-success mb-3" />
                            <h4 className="text-success">¡Excelente!</h4>
                            <p className="text-muted">No hay productos con bajo stock en este momento.</p>
                            <p className="text-muted">Todos los productos tienen stock suficiente.</p>
                            <button
                                className="btn btn-primary mt-2"
                                onClick={handleBack}
                            >
                                <FaArrowLeft className="me-2" />
                                Volver al Inicio
                            </button>
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table table-striped table-hover">
                                <thead className="table-dark">
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
                                    {products.map((product, index) => {
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

            {/* Modal para PDF */}
            {showPDFModal && (
                <PDFLowStockReport
                    lowStockProducts={products}
                    onClose={() => setShowPDFModal(false)}
                />
            )}
        </div>
    );
};

export default LowStockProducts;