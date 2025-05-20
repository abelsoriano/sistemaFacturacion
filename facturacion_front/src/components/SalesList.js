import React, { useState, useEffect, useMemo } from 'react';
import DataTable from 'react-data-table-component';
import api from '../services/api';
import { Link } from "react-router-dom";
import Swal from "sweetalert2";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import { BsEyeFill as VerIcon, BsPencilFill as EditarIcon, BsTrashFill as EliminarIcon, BsFilter as FilterIcon, BsFileExcel as ExcelIcon, BsPlusCircle as AddIcon } from 'react-icons/bs';
import {stylesAlmacens, styles,} from "../herpert";

const SalesList = () => {
  const [sales, setSales] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [selectedDateRange, setSelectedDateRange] = useState({
    start: '',
    end: ''
  });
  const navigate = useNavigate();
  const [hoverStates, setHoverStates] = useState({
          cancel: false,
          submit: false
        });

  // Función para normalizar fechas (elimina la información de zona horaria)
  const normalizeDate = (dateString) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  };

  // Función para obtener las ventas
  const fetchSales = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('/sales/list/');
      setSales(response.data);
    } catch (err) {
      setError('Error al cargar las ventas. Por favor, intente nuevamente.');
      console.error('Error fetching sales:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    navigate('/');
  };

  useEffect(() => {
    fetchSales();
  }, []);

  // Filtrado optimizado con useMemo
  const filteredSales = useMemo(() => {
    let result = [...sales];
    
    // Filtro por búsqueda
    if (search) {
      const searchTerm = search.toLowerCase();
      result = result.filter((sale) => {
        const customer = sale.customer ? sale.customer.toLowerCase() : "";
        const date = new Date(sale.date).toLocaleString().toLowerCase();
        return customer.includes(searchTerm) || date.includes(searchTerm);
      });
    }
    
    // Filtro por rango de fechas
    if (selectedDateRange.start && selectedDateRange.end) {
      const startDate = normalizeDate(selectedDateRange.start);
      const endDate = normalizeDate(selectedDateRange.end);
      
      result = result.filter(sale => {
        const saleDate = normalizeDate(sale.date);
        if (!saleDate) return false;
        return saleDate >= startDate && saleDate <= endDate;
      });
    }
    
    return result;
  }, [sales, search, selectedDateRange]);

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
        setSales(prev => prev.filter(sale => sale.id !== id));
        showSuccessAlert("Eliminado", "La venta ha sido eliminada correctamente.");
      } catch (error) {
        showErrorAlert("Error", "No se pudo eliminar la venta. Por favor, intente nuevamente.");
        console.error('Error deleting sale:', error);
      }
    }
  };

  const handleViewDetails = (details) => {
    if (!details || details.length === 0) {
      Swal.fire({
        title: "Detalles de la Venta",
        text: "No hay detalles disponibles para esta venta.",
        icon: "info",
        confirmButtonText: "Cerrar"
      });
      return;
    }

    const totalVenta = details.reduce((acc, item) => acc + (parseFloat(item.subtotal) || 0), 0);

    const tableRows = details.map((item) => (`
      <tr>
        <td style="padding: 6px; border: 1px solid #ddd;">${item.product_name || 'N/A'}</td>
        <td style="padding: 6px; border: 1px solid #ddd; text-align: center;">${item.quantity || 0}</td>
        <td style="padding: 6px; border: 1px solid #ddd; text-align: right;">$${parseFloat(item.price || 0).toFixed(2)}</td>
        <td style="padding: 6px; border: 1px solid #ddd; text-align: right;">$${parseFloat(item.subtotal || 0).toFixed(2)}</td>
      </tr>
    `)).join("");

    const htmlContent = `
      <div style="max-height: 400px; overflow-y: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
          <thead>
            <tr style="background-color: #f8f9fa;">
              <th style="padding: 8px; border: 1px solid #ddd;">Producto</th>
              <th style="padding: 8px; border: 1px solid #ddd; width: 80px;">Cantidad</th>
              <th style="padding: 8px; border: 1px solid #ddd; width: 100px;">Precio</th>
              <th style="padding: 8px; border: 1px solid #ddd; width: 120px;">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            ${tableRows}
            <tr style="background-color: #f8f9fa; font-weight: bold;">
              <td colspan="3" style="padding: 8px; text-align: right; border: 1px solid #ddd;">Total:</td>
              <td style="padding: 8px; text-align: right; border: 1px solid #ddd;">$${totalVenta.toFixed(2)}</td>
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
    if (filteredSales.length === 0) {
      showErrorAlert("Error", "No hay datos para exportar.");
      return;
    }

    try {
      const worksheet = XLSX.utils.json_to_sheet(filteredSales.map(sale => ({
        'ID': sale.id,
        'Mecánico': sale.customer || 'N/A',
        'Fecha': new Date(sale.date).toLocaleString(),
        'Total': `$${parseFloat(sale.total || 0).toFixed(2)}`,
        'Productos Vendidos': sale.details?.length || 0
      })));

      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Ventas");
      XLSX.writeFile(workbook, `reporte_ventas_${new Date().toISOString().slice(0,10)}.xlsx`);
    } catch (error) {
      showErrorAlert("Error", "No se pudo generar el archivo Excel.");
      console.error('Error exporting to Excel:', error);
    }
  };

  const columns = [
    {
      name: 'ID',
      selector: row => row.id,
      sortable: true,
      width: '80px'
    },
    {
      name: 'Mecánico',
      selector: row => row.customer || 'N/A',
      sortable: true,
      cell: row => <span title={row.customer || 'N/A'}>{row.customer || 'N/A'}</span>
    },
    {
      name: 'Fecha',
      selector: row => new Date(row.date).toLocaleString(),
      sortable: true,
      cell: row => <span title={new Date(row.date).toLocaleString()}>
        {new Date(row.date).toLocaleDateString()}
      </span>,
      width: '150px'
    },
    {
      name: 'Total',
      selector: row => parseFloat(row.total || 0),
      sortable: true,
      cell: row => `$${parseFloat(row.total || 0).toFixed(2)}`,
      width: '120px'
    },
    {
      name: 'Productos',
      selector: row => row.details?.length || 0,
      sortable: true,
      width: '100px',
      cell: row => <span className="badge bg-primary">{row.details?.length || 0}</span>
    },
    {
      name: 'Acciones',
      cell: row => (
        <div className="d-flex justify-content-center gap-2">
          <button
            className="btn btn-info btn-sm"
            onClick={() => handleViewDetails(row.details)}
            title="Ver Detalles"
          >
            <VerIcon />
          </button>
          <button
            className="btn btn-primary btn-sm"
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
      width: '180px',
      ignoreRowClick: true,
      allowOverflow: true
    },
  ];

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1 className="mb-0">Lista de Ventas</h1>
        <button
          onClick={handleCancel}
          onMouseEnter={() =>
            setHoverStates((prev) => ({ ...prev, cancel: true }))
          }
          onMouseLeave={() =>
            setHoverStates((prev) => ({ ...prev, cancel: false }))
          }
          style={{
            ...styles.button,
            ...styles.cancelButton,
            ...(hoverStates.cancel ? styles.cancelButtonHover : {}),
          }}
        >
          Cancela
        </button>
        <Link to="/sales" className="btn btn-primary">
          <AddIcon className="me-2" />
          Crear Venta
        </Link>
      </div>

      
        
      

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <div className="input-group">
                <span className="input-group-text">
                  <i className="bi bi-search"></i>
                </span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Buscar por mecánico o fecha..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            <div className="col-md-3">
              <input
                type="date"
                className="form-control"
                value={selectedDateRange.start}
                onChange={(e) =>
                  setSelectedDateRange((prev) => ({
                    ...prev,
                    start: e.target.value,
                  }))
                }
              />
            </div>

            <div className="col-md-3">
              <input
                type="date"
                className="form-control"
                value={selectedDateRange.end}
                onChange={(e) =>
                  setSelectedDateRange((prev) => ({
                    ...prev,
                    end: e.target.value,
                  }))
                }
                min={selectedDateRange.start}
              />
            </div>

            <div className="col-md-12 d-flex gap-2">
              <button
                className="btn btn-outline-secondary d-flex align-items-center gap-1"
                onClick={() => {
                  setSelectedDateRange({ start: "", end: "" });
                  setSearch("");
                }}
                disabled={
                  !search && !selectedDateRange.start && !selectedDateRange.end
                }
              >
                <i className="bi bi-x-lg"></i> Limpiar Filtros
              </button>

              <button
                className="btn btn-success d-flex align-items-center gap-1 ms-auto"
                onClick={exportToExcel}
                disabled={filteredSales.length === 0}
              >
                <ExcelIcon /> Exportar
              </button>
            </div>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Cargando...</span>
          </div>
          <p className="mt-2">Cargando ventas...</p>
        </div>
      ) : error ? (
        <div
          className="alert alert-danger d-flex align-items-center"
          role="alert"
        >
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          <div>{error}</div>
          <button
            className="btn btn-sm btn-outline-danger ms-auto"
            onClick={fetchSales}
          >
            Reintentar
          </button>
        </div>
      ) : (
        <div className="card shadow-sm">
          <DataTable
            columns={columns}
            data={filteredSales}
            pagination
            paginationPerPage={10}
            paginationRowsPerPageOptions={[10, 25, 50, 100]}
            highlightOnHover
            striped
            responsive
            noDataComponent={
              <div className="alert alert-info m-3">
                {search || selectedDateRange.start || selectedDateRange.end
                  ? "No se encontraron ventas con los filtros aplicados."
                  : "No hay ventas registradas."}
              </div>
            }
            customStyles={{
              headCells: {
                style: {
                  backgroundColor: "#f8f9fa",
                  fontWeight: "bold",
                },
              },
            }}
          />
        </div>
      )}
    </div>
  );
};

export default SalesList;