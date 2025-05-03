import React, { useState, useEffect } from 'react';
import DataTable from 'react-data-table-component';
import api from '../services/api';
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import { useNavigate } from 'react-router-dom';

const SalesList = () => {
  const [sales, setSales] = useState([]);
  const [filteredSales, setFilteredSales] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const fetchSales = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.get('/sales/list/');
        setFilteredSales(response.data);
        setSales(response.data);
      } catch (err) {
        setError('Error al cargar las ventas.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchSales();
  }, []);

  const handleEdit = (id) => {
    navigate(`/SalesForm/${id}`);
  };

 

  const handleDelete = async (id) => {
    const result = await showConfirmationAlert(
      "¿Estás seguro?",
      "Esta acción no se puede deshacer."
    );

  if (result.isConfirmed) {
    try {
      await api.delete(`/salesUpdate/${id}/`);
      const updatedSales = sales.filter((sale) => sale.id !== id);
      setSales(updatedSales);
      setFilteredSales(updatedSales);
      showSuccessAlert("Eliminado", "La venta ha sido eliminada.");
    } catch (error) {
      showErrorAlert("Error", "No se pudo eliminar la venta.");
    }
  }
};


  const handleSearch = (event) => {
    const searchTerm = event.target.value.toLowerCase();
    setSearch(searchTerm);
  
    const filtered = sales.filter((sale) => {
      const customer = sale.customer ? sale.customer.toLowerCase() : ""; // Valor predeterminado
      const date = new Date(sale.date).toLocaleString().toLowerCase();
      return customer.includes(searchTerm) || date.includes(searchTerm);
    });
  
    setFilteredSales(filtered);
  };

  const handleViewDetails = (details) => {
    // Calculamos el total de la venta
    const totalVenta = details.reduce((acc, item) => acc + parseFloat(item.subtotal), 0);
  
    const tableRows = details
      .map(
        (item) => `
          <tr>
            <td style="padding: 6px; border: 1px solid #ccc;">${item.product_name}</td>
            <td style="padding: 6px; border: 1px solid #ccc;">${item.quantity}</td>
            <td style="padding: 6px; border: 1px solid #ccc;">$${parseFloat(item.price).toFixed(2)}</td>
            <td style="padding: 6px; border: 1px solid #ccc;">$${parseFloat(item.subtotal).toFixed(2)}</td>
          </tr>
        `
      )
      .join("");
  
    const htmlContent = `
      <div style="max-height: 300px; overflow-y: auto;">
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th style="padding: 6px; border: 1px solid #ccc; background-color: #f5f5f5;">Producto</th>
              <th style="padding: 6px; border: 1px solid #ccc; background-color: #f5f5f5;">Cantidad</th>
              <th style="padding: 6px; border: 1px solid #ccc; background-color: #f5f5f5;">Precio</th>
              <th style="padding: 6px; border: 1px solid #ccc; background-color: #f5f5f5;">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            ${tableRows}
            <tr>
              <td colspan="3" style="padding: 8px; text-align: right; font-weight: bold; border: 1px solid #ccc;">Total:</td>
              <td style="padding: 8px; font-weight: bold; border: 1px solid #ccc;">$${totalVenta.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  
    Swal.fire({
      title: "Detalles de la Venta",
      html: htmlContent,
      icon: "info",
      confirmButtonText: "Cerrar",
      width: "700px",
      customClass: {
        popup: 'custom-swal-popup',
      },
    });
  };
  

  

  const columns = [
    {
      name: 'ID',
      selector: (row) => row.id,
      sortable: true,
    },
    {
      name: 'Mecanico',
      selector: (row) => row.customer || 'n/a',
      sortable: true,
    },
    {
      name: 'Fecha',
      selector: (row) => new Date(row.date).toLocaleString(),
      sortable: true,
    },
    {
      name: 'Precio',
      cell: (row) => `$${parseFloat(row.total).toFixed(2)}`,
      sortable: true,
    },
    {
      name: 'Acciones',
      cell: (row) => (
        <div>
          <button
            className="btn btn-info btn-sm me-2"
            onClick={() => handleViewDetails(row.details)}
          >
            Ver Detalles
          </button>
          <button
            className="btn btn-primary btn-sm me-2"
            onClick={() => handleEdit(row.id)}
          >
            Editar
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => handleDelete(row.id)}
          >
            Elimina
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="container mt-5">
      <h1 className="mb-4">Lista de Ventas</h1>
      <div className="mb-3 d-flex">
        <input
          type="text"
          className="form-control me-2"
          placeholder="Buscar ventas..."
          value={search}
          onChange={handleSearch}
        />
      </div>
      {isLoading && <p>Cargando ventas...</p>}
      {error && <p className="text-danger">Error: {error}</p>}
      {!isLoading && (
        <DataTable
          title="Listado de Ventas"
          columns={columns}
          data={filteredSales}
          highlightOnHover
          pagination
          striped
          responsive
          noDataComponent={<p>No se encontraron ventas.</p>}
        />
      )}
      <Link to="/sales" className="btn btn-primary m-2">Crear Venta</Link>
      <Link to="/" className="btn btn-danger m-2">Cancelar</Link>
    </div>
  );
};

export default SalesList;
