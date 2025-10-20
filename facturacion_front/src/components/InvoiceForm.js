import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import { FaSave, FaPlus, FaTrash, FaArrowLeft, FaPrint, FaCheck } from "react-icons/fa";

const InvoiceForm = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [clients, setClients] = useState([]);
    const [products, setProducts] = useState([]);
    const [productDetails, setProductDetails] = useState({});
    const [invoice, setInvoice] = useState({
        client: "",
        details: [],
        status: "pending",
        date: new Date().toISOString().split('T')[0],
        notes: ""
    });
    const [errors, setErrors] = useState({});

    // Cargar datos iniciales
    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                // Cargar clientes
                const clientsResponse = await api.get("clients/");
                setClients(clientsResponse.data);
                
                // Cargar productos con detalles
                const productsResponse = await api.get("products/");
                setProducts(productsResponse.data);
                
                // Crear objeto para acceso rápido a detalles de productos
                const productsMap = {};
                productsResponse.data.forEach(product => {
                    productsMap[product.id] = product;
                });
                setProductDetails(productsMap);
                
                // Si hay un ID, cargar datos de la factura existente
                if (id) {
                    const invoiceResponse = await api.get(`invoices/${id}/`);
                    const invoiceData = invoiceResponse.data;
                    setInvoice(invoiceData);
                }
            } catch (error) {
                console.error("Error al cargar datos iniciales:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [id]);

    // Manejar cambios en el cliente seleccionado
    const handleClientChange = (e) => {
        setInvoice({ ...invoice, client: e.target.value });
        
        // Limpiar error de cliente si existe
        if (errors.client) {
            setErrors({ ...errors, client: null });
        }
    };

    // Agregar una nueva línea de detalle
    const handleAddDetail = () => {
        setInvoice({
            ...invoice,
            details: [...invoice.details, { product: "", quantity: 1, price: 0, subtotal: 0 }],
        });
    };

    // Eliminar una línea de detalle
    const handleRemoveDetail = (indexToRemove) => {
        setInvoice({
            ...invoice,
            details: invoice.details.filter((_, index) => index !== indexToRemove),
        });
    };

    // Manejar cambios en los detalles de la factura
    const handleDetailChange = (index, field, value) => {
        const updatedDetails = [...invoice.details];
        
        // Convertir a número si es un campo numérico
        if (field === "price" || field === "quantity") {
            value = Number(value);
        }
        
        updatedDetails[index][field] = value;
        
        // Si el campo es "product", actualizar el precio automáticamente
        if (field === "product" && value && productDetails[value]) {
            updatedDetails[index].price = productDetails[value].price || 0;
        }
        
        // Calcular subtotal
        if (field === "product" || field === "price" || field === "quantity") {
            updatedDetails[index].subtotal = 
                updatedDetails[index].quantity * updatedDetails[index].price;
        }
        
        setInvoice({ ...invoice, details: updatedDetails });
        
        // Limpiar errores si existen
        if (errors.details) {
            setErrors({ ...errors, details: null });
        }
    };

    // Calcular total de la factura
    const calculateTotal = () => {
        return invoice.details.reduce((sum, detail) => sum + (detail.subtotal || detail.quantity * detail.price), 0);
    };

    // Validar el formulario
    const validateForm = () => {
        const newErrors = {};
        
        if (!invoice.client) {
            newErrors.client = "Debe seleccionar un cliente";
        }
        
        if (invoice.details.length === 0) {
            newErrors.details = "Debe agregar al menos un detalle a la factura";
        } else {
            // Verificar que todos los detalles tengan producto y cantidad
            const invalidDetails = invoice.details.some(
                detail => !detail.product || detail.quantity <= 0
            );
            
            if (invalidDetails) {
                newErrors.details = "Todos los detalles deben tener producto y cantidad válida";
            }
        }
        
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    // Cambiar el estado de la factura
    const handleStatusChange = async (newStatus) => {
        try {
            await api.patch(`invoices/${id}/`, { status: newStatus });
            setInvoice({ ...invoice, status: newStatus });
            alert(`Factura marcada como ${newStatus}`);
        } catch (error) {
            console.error(`Error al cambiar estado a ${newStatus}:`, error);
        }
    };

    // Manejar el envío del formulario
    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        setIsLoading(true);
        
        try {
            let response;
            
            // Preparar datos para el envío
            const invoiceData = {
                ...invoice,
                total: calculateTotal()
            };
            
            if (id) {
                // Actualizar factura existente
                response = await api.put(`invoices/${id}/`, invoiceData);
                alert("Factura actualizada con éxito!");
            } else {
                // Crear nueva factura
                response = await api.post("invoices/", invoiceData);
                alert("Factura creada con éxito!");
            }
            
            // Redireccionar a la lista de facturas o a la vista de detalle
            navigate(`/invoice-detail/${response.data.id}`);
        } catch (error) {
            console.error("Error al guardar factura:", error);
            alert("Error al guardar la factura. Por favor intente nuevamente.");
        } finally {
            setIsLoading(false);
        }
    };

    // Manejar la impresión de la factura
    const handlePrint = () => {
        if (id) {
            window.open(`/invoice-print/${id}`, '_blank');
        }
    };

    if (isLoading) {
        return (
            <div className="d-flex justify-content-center mt-5">
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Cargando...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="container py-4">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <h2 className="mb-0">{id ? "Editar Factura" : "Crear Nueva Factura"}</h2>
                <div>
                    <button 
                        onClick={() => navigate('/invoice-list')} 
                        className="btn btn-outline-secondary me-2"
                    >
                        <FaArrowLeft className="me-2" /> Volver
                    </button>
                    {id && (
                        <>
                            <button 
                                onClick={handlePrint} 
                                className="btn btn-outline-primary me-2"
                            >
                                <FaPrint className="me-2" /> Imprimir
                            </button>
                            {invoice.status === "pending" && (
                                <button 
                                    onClick={() => handleStatusChange("completed")} 
                                    className="btn btn-success me-2"
                                >
                                    <FaCheck className="me-2" /> Marcar como Completada
                                </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            <div className="card shadow-sm">
                <div className="card-body">
                    <form onSubmit={handleSubmit}>
                        <div className="row mb-4">
                            <div className="col-md-6">
                                <div className="mb-3">
                                    <label htmlFor="client" className="form-label">Cliente:</label>
                                    <select
                                        id="client"
                                        className={`form-select ${errors.client ? 'is-invalid' : ''}`}
                                        value={invoice.client}
                                        onChange={handleClientChange}
                                        disabled={isLoading}
                                    >
                                        <option value="">Seleccionar Cliente</option>
                                        {clients.map((client) => (
                                            <option key={client.id} value={client.id}>
                                                {client.name}
                                            </option>
                                        ))}
                                    </select>
                                    {errors.client && (
                                        <div className="invalid-feedback">{errors.client}</div>
                                    )}
                                </div>
                            </div>
                            <div className="col-md-6">
                                <div className="mb-3">
                                    <label htmlFor="date" className="form-label">Fecha:</label>
                                    <input
                                        type="date"
                                        id="date"
                                        className="form-control"
                                        value={invoice.date}
                                        onChange={(e) => setInvoice({ ...invoice, date: e.target.value })}
                                        disabled={isLoading}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="mb-4">
                            <div className="d-flex justify-content-between align-items-center mb-3">
                                <h5 className="mb-0">Detalles de la Factura</h5>
                                <button
                                    type="button"
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={handleAddDetail}
                                    disabled={isLoading}
                                >
                                    <FaPlus className="me-1" /> Agregar Ítem
                                </button>
                            </div>
                            
                            {errors.details && (
                                <div className="alert alert-danger py-2">{errors.details}</div>
                            )}

                            <div className="table-responsive">
                                <table className="table table-bordered table-hover">
                                    <thead className="table-light">
                                        <tr>
                                            <th>Producto</th>
                                            <th>Cantidad</th>
                                            <th>Precio Unitario</th>
                                            <th>Subtotal</th>
                                            <th style={{ width: "50px" }}></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {invoice.details.length === 0 ? (
                                            <tr>
                                                <td colSpan="5" className="text-center py-3 text-muted">
                                                    No hay ítems agregados. Haga clic en "Agregar Ítem".
                                                </td>
                                            </tr>
                                        ) : (
                                            invoice.details.map((detail, index) => (
                                                <tr key={index}>
                                                    <td>
                                                        <select
                                                            className="form-select form-select-sm"
                                                            value={detail.product}
                                                            onChange={(e) => handleDetailChange(index, "product", e.target.value)}
                                                            disabled={isLoading}
                                                        >
                                                            <option value="">Seleccionar Producto</option>
                                                            {products.map((product) => (
                                                                <option key={product.id} value={product.id}>
                                                                    {product.name}
                                                                </option>
                                                            ))}
                                                        </select>
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-control form-control-sm"
                                                            min="1"
                                                            value={detail.quantity}
                                                            onChange={(e) => handleDetailChange(index, "quantity", e.target.value)}
                                                            disabled={isLoading}
                                                        />
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="form-control form-control-sm"
                                                            step="0.01"
                                                            min="0"
                                                            value={detail.price}
                                                            onChange={(e) => handleDetailChange(index, "price", e.target.value)}
                                                            disabled={isLoading}
                                                        />
                                                    </td>
                                                    <td className="text-end">
                                                        {(detail.subtotal || detail.quantity * detail.price).toFixed(2)}
                                                    </td>
                                                    <td className="text-center">
                                                        <button
                                                            type="button"
                                                            className="btn btn-sm btn-outline-danger"
                                                            onClick={() => handleRemoveDetail(index)}
                                                            disabled={isLoading}
                                                        >
                                                            <FaTrash />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                    <tfoot>
                                        <tr>
                                            <td colSpan="3" className="text-end fw-bold">Total:</td>
                                            <td className="text-end fw-bold">${calculateTotal().toFixed(2)}</td>
                                            <td></td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        </div>

                        <div className="mb-4">
                            <label htmlFor="notes" className="form-label">Notas:</label>
                            <textarea
                                id="notes"
                                className="form-control"
                                rows="3"
                                value={invoice.notes || ""}
                                onChange={(e) => setInvoice({ ...invoice, notes: e.target.value })}
                                disabled={isLoading}
                                placeholder="Agregar notas o comentarios adicionales..."
                            ></textarea>
                        </div>

                        <div className="d-flex justify-content-end">
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={isLoading}
                            >
                                <FaSave className="me-2" /> 
                                {id ? "Actualizar Factura" : "Guardar Factura"}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default InvoiceForm;