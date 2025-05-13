import React, { useState, useEffect } from 'react';
import DataTable from 'react-data-table-component';
import api from '../services/api';
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
// Reemplaza la importación de bootstrap-icons-react con:
import { BsEyeFill as VerIcon, BsPencilFill as EditarIcon, BsTrashFill as EliminarIcon } from 'react-icons/bs';

const SalesList = () => {
  const [sales, setSales] = useState([]);
  const [filteredSales, setFilteredSales] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [selectedDateRange, setSelectedDateRange] = useState({
    start: '',
    end: ''
  });
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
      const customer = sale.customer ? sale.customer.toLowerCase() : "";
      const date = new Date(sale.date).toLocaleString().toLowerCase();
      return customer.includes(searchTerm) || date.includes(searchTerm);
    });

    setFilteredSales(filtered);
  };

  const handleDateFilter = () => {
    if (!selectedDateRange.start || !selectedDateRange.end) {
      setFilteredSales(sales);
      return;
    }

    const filtered = sales.filter(sale => {
      const saleDate = new Date(sale.date);
      const startDate = new Date(selectedDateRange.start);
      const endDate = new Date(selectedDateRange.end);

      return saleDate >= startDate && saleDate <= endDate;
    });

    setFilteredSales(filtered);
  };

  const handleViewDetails = (details) => {
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

  const exportToExcel = () => {
    const worksheet = XLSX.utils.json_to_sheet(filteredSales.map(sale => ({
      'ID': sale.id,
      'Mecánico': sale.customer || 'n/a',
      'Fecha': new Date(sale.date).toLocaleString(),
      'Total': `$${parseFloat(sale.total).toFixed(2)}`,
      'Productos Vendidos': sale.details.length
    })));

    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Ventas");
    XLSX.writeFile(workbook, "reporte_ventas.xlsx");
  };

   const columns = [
    {
      name: 'ID',
      selector: (row) => row.id,
      sortable: true,
      width: '80px'
    },
    {
      name: 'Mecánico',
      selector: (row) => row.customer || 'n/a',
      sortable: true,
    },
    {
      name: 'Fecha',
      selector: (row) => new Date(row.date).toLocaleString(),
      sortable: true,
    },
    {
      name: 'Total',
      cell: (row) => `$${parseFloat(row.total).toFixed(2)}`,
      sortable: true,
      width: '120px'
    },
    {
      name: 'Productos',
      cell: (row) => row.details.length,
      sortable: true,
      width: '100px'
    },
    {
      name: 'Acciones',
      cell: (row) => (
        <div className="d-flex justify-content-center">
          <button
            className="btn btn-info btn-sm me-2"
            onClick={() => handleViewDetails(row.details)}
            title="Ver Detalles"
          >
            <VerIcon />
          </button>
          <button
            className="btn btn-primary btn-sm me-2"
            onClick={() => handleEdit(row.id)}
            title="Editar"
          >
            <EditarIcon />
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => handleDelete(row.id)}
            title="Eliminar"
          >
            <EliminarIcon />
          </button>
        </div>
      ),
      width: '180px'
    },
  ];

  return (
    <div className="container mt-5">
      <h1 className="mb-4">Lista de Ventas</h1>

      <div className="mb-4 card p-3">
        <div className="row">
          <div className="col-md-6 mb-2">
            <input
              type="text"
              className="form-control"
              placeholder="Buscar por mecánico o fecha..."
              value={search}
              onChange={handleSearch}
            />
          </div>
          <div className="col-md-3 mb-2">
            <input
              type="date"
              className="form-control"
              value={selectedDateRange.start}
              onChange={(e) => setSelectedDateRange({...selectedDateRange, start: e.target.value})}
            />
          </div>
          <div className="col-md-3 mb-2">
            <input
              type="date"
              className="form-control"
              value={selectedDateRange.end}
              onChange={(e) => setSelectedDateRange({...selectedDateRange, end: e.target.value})}
            />
          </div>
          <div className="col-md-12">
            <button className="btn btn-secondary me-2" onClick={handleDateFilter}>
              Filtrar por Fecha
            </button>
            <button className="btn btn-success me-2" onClick={exportToExcel}>
              Exportar a Excel
            </button>
            <Link to="/sales" className="btn btn-primary me-2">
              Crear Venta
            </Link>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="text-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Cargando...</span>
          </div>
          <p>Cargando ventas...</p>
        </div>
      )}

      {error && (
        <div className="alert alert-danger" role="alert">
          Error: {error}
        </div>
      )}

      {!isLoading && (
        <DataTable
          title="Listado de Ventas"
          columns={columns}
          data={filteredSales}
          highlightOnHover
          pagination
          striped
          responsive
          noDataComponent={
            <div className="alert alert-info mt-3">
              No se encontraron ventas con los filtros aplicados.
            </div>
          }
        />
      )}
    </div>
  );
};

export default SalesList;