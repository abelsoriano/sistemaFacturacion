import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";

const InvoiceForm = () => {
    const [clients, setClients] = useState([]);
    const [products, setProducts] = useState([]);
    const { id } = useParams();
    const [invoice, setInvoice] = useState({
        client: "",
        details: [],
        status: "Pending",
    });

    useEffect(() => {
        api.get("clients/")
            .then((response) => setClients(response.data))
            .catch((error) => console.error("Error al obtener clientes:", error));
        api.get("products/")
            .then((response) => setProducts(response.data))
            .catch((error) => console.error("Error al obtener productos:", error));
    }, []);

    const handleAddDetail = () => {
        setInvoice({
            ...invoice,
            details: [...invoice.details, { product: "", quantity: 1, price: 0 }],
        });
    };

    const handleDetailChange = (index, field, value) => {
        const updatedDetails = [...invoice.details];
        updatedDetails[index][field] = field === "price" || field === "quantity" ? Number(value) : value;
        setInvoice({ ...invoice, details: updatedDetails });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        await api.post("invoices/", invoice)
            .then((response) => {
                alert("Factura creada con éxito!");
                console.log(response.data);
            })
            .catch((error) => console.error("Error al crear factura:", error));
    };

    return (
        <div className="container mt-5">
        <h2 className="text-center mb-4">{id ? "Editar Categoría" : "Agregar Categoría"}</h2>
        <form onSubmit={handleSubmit} className="shadow p-4 rounded bg-light">
            <div className="mb-4">
                <h4 className="text-center">Crear Factura</h4>
                <label htmlFor="ivoice" className="form-label">
                    Cliente:
                </label>
                <select
                    className="form-select"
                    id="ivoice"
                    name="ivoice"
                    value={invoice.client}
                    onChange={(e) => setInvoice({ ...invoice, client: e.target.value })}
                >
                    <option value="">Seleccionar Cliente</option>
                    {clients.length > 0 ? (
                        clients.map((client) => (
                            <option key={client.id} value={client.id}>
                                {client.name}
                            </option>
                        ))
                    ) : (
                        <option disabled>Cargando clientes...</option>
                    )}
                </select>
            </div>
    
            <h5 className="mt-4">Detalles de Factura</h5>
            {invoice.details.map((detail, index) => (
                <div key={index} className="row g-3 align-items-center mb-3">
                    <div className="col-md-4">
                        <label className="form-label">Producto:</label>
                        <select
                            className="form-select"
                            value={detail.product}
                            onChange={(e) => handleDetailChange(index, "product", e.target.value)}
                        >
                            <option value="">Seleccionar Producto</option>
                            {products.map((product) => (
                                <option key={product.id} value={product.id}>
                                    {product.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="col-md-3">
                        <label className="form-label">Cantidad:</label>
                        <input
                            className="form-control"
                            type="number"
                            placeholder="Cantidad"
                            value={detail.quantity}
                            onChange={(e) => handleDetailChange(index, "quantity", e.target.value)}
                        />
                    </div>
                    <div className="col-md-3">
                        <label className="form-label">Precio:</label>
                        <input
                            className="form-control"
                            type="number"
                            placeholder="Precio"
                            value={detail.price}
                            onChange={(e) => handleDetailChange(index, "price", e.target.value)}
                        />
                    </div>
                </div>
            ))}
            <div className="d-flex justify-content-between mt-4">
                <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleAddDetail}
                >
                    Agregar Detalle
                </button>
                <button type="submit" className="btn btn-primary">
                    Guardar Factura
                </button>
            </div>
        </form>
    </div>
    
    );
};

export default InvoiceForm;
