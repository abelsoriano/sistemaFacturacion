import React, { useState, useEffect, useMemo } from 'react';
import { ArrowUp, Edit, ArrowDown, Trash, ChevronsLeft, ChevronLeft, ChevronRight, ChevronsRight, FileX, Package, Plus, Search } from 'lucide-react';
import { useNavigate } from "react-router-dom";
import api from "../services/api"; 
import {stylesAlmacens, styles, showConfirmationAlert, showSuccessAlert, showErrorAlert} from "../herpert";

const LabourList = () => {
  // Estados
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'asc' });
  const [pagination, setPagination] = useState({
    currentPage: 1,
    itemsPerPage: 10,
    totalItems: 0
  });
  const [hoveredRow, setHoveredRow] = useState(null);
  const [buttonHoverStates, setButtonHoverStates] = useState({});
  const [hoverStates, setHoverStates] = useState({
    cancel: false,
    submit: false
  });

  const navigate = useNavigate();

  // Handlers
  const newItem = () => navigate('/register-labour');

  const handleDelete = async (id) => {
    const result = await showConfirmationAlert(
      "¿Estás seguro?",
      "Esta acción no se puede deshacer."
    );
    
    if (result.isConfirmed) {
      try {
        await api.delete(`/labours/${id}/`);
        const updatedLabour = items.filter(item => item.id !== id);
        setItems(updatedLabour);
        showSuccessAlert("Eliminado", "El servicio ha sido eliminado.");
      } catch (error) {
        showErrorAlert("Error", "No se pudo eliminar el servicio.");
      }
    }
  };

  const handleCancel = () => navigate('/');

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const handleEdit = (itemId) => navigate(`/register-labour/${itemId}`);

  const handleButtonHover = (id, isHovered) => {
    setButtonHoverStates(prev => ({ ...prev, [id]: isHovered }));
  };

  const handlePageChange = (page) => {
    setPagination(prev => ({ ...prev, currentPage: page }));
  };

  // Efectos
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await api.get('labours/');
        setItems(response.data);
        setPagination(prev => ({ 
          ...prev, 
          totalItems: response.data.length 
        }));
      } catch (error) {
        console.error('Error al cargar datos', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Datos procesados
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      return (
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    });
  }, [items, searchTerm]);

  const sortedItems = useMemo(() => {
    let sortableItems = [...filteredItems];
    if (sortConfig.key) {
      sortableItems.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableItems;
  }, [filteredItems, sortConfig]);

  const paginatedItems = useMemo(() => {
    const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
    return sortedItems.slice(startIndex, startIndex + pagination.itemsPerPage);
  }, [sortedItems, pagination.currentPage, pagination.itemsPerPage]);

  const totalPages = Math.ceil(filteredItems.length / pagination.itemsPerPage);

  // Render helpers
  const renderSortableHeader = (key, label) => {
    return (
      <th
        style={{
          ...stylesAlmacens.tableHeader,
          ...stylesAlmacens.tableHeaderSortable,
          ...(sortConfig.key === key ? stylesAlmacens.tableHeaderSortableActive : {})
        }}
        onClick={() => handleSort(key)}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {label}
          <span style={{ marginLeft: '4px' }}>
            {sortConfig.key === key && sortConfig.direction === 'asc' ? (
              <ArrowUp size={16} />
            ) : sortConfig.key === key && sortConfig.direction === 'desc' ? (
              <ArrowDown size={16} />
            ) : null}
          </span>
        </div>
      </th>
    );
  };

  return (
    <div style={stylesAlmacens.container}>
      <div style={stylesAlmacens.header}>
        <div style={stylesAlmacens.headerTitle}>
          <span style={{ marginRight: "8px" }}>
            <Package size={20} />
          </span>
          <span>Lista de Servicio prestado</span>
        </div>
        <button
          style={{
            ...stylesAlmacens.button,
            ...stylesAlmacens.primaryButton,
            ...(buttonHoverStates["addNew"] ? stylesAlmacens.primaryButtonHover : {}),
          }}
          onMouseEnter={() => handleButtonHover("addNew", true)}
          onMouseLeave={() => handleButtonHover("addNew", false)}
          onClick={newItem}
        >
          <span style={{ marginRight: "8px" }}>
            <Plus size={16} />
          </span>
          Nuevo Servicio
        </button>
      </div>

      <div style={stylesAlmacens.searchFilterContainer}>
        <div style={stylesAlmacens.searchContainer}>
          <input
            type="text"
            placeholder="Buscar servicios..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={stylesAlmacens.searchInput}
          />
          <div style={stylesAlmacens.searchIcon}>
            <Search size={16} />
          </div>
        </div>
      </div>

      {loading ? (
        <div style={stylesAlmacens.loadingContainer}>
          <div style={stylesAlmacens.spinner}></div>
          <p>Cargando servicios...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div style={stylesAlmacens.emptyState}>
          <FileX size={48} />
          <h3>No se encontraron servicios</h3>
          <p>
            Intenta cambiar los filtros o añade nuevos servicios.
          </p>
        </div>
      ) : (
        <>
          <div style={stylesAlmacens.tableContainer}>
            <table style={stylesAlmacens.table}>
              <thead>
                <tr>
                  {renderSortableHeader("name", "Nombre")}
                  <th style={stylesAlmacens.tableHeader}>Descripción</th>
                  {renderSortableHeader("price", "Precio")}
                  {renderSortableHeader("factura_asociada", "Factura Relacionada")}
                  <th style={stylesAlmacens.tableHeader}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map((item) => (
                  <tr
                    key={item.id}
                    style={{
                      ...stylesAlmacens.tableRow,
                      ...(hoveredRow === item.id ? stylesAlmacens.tableRowHover : {}),
                    }}
                    onMouseEnter={() => setHoveredRow(item.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <td style={stylesAlmacens.tableCell}>
                      <div style={stylesAlmacens.itemName}>{item.name}</div>
                    </td>
                    <td style={stylesAlmacens.tableCell}>{item.description}</td>
                    <td style={stylesAlmacens.tableCell}>{item.price}</td>
                    <td style={stylesAlmacens.tableCell}>{item.factura_asociada}</td>
                    <td style={stylesAlmacens.tableCell}>
                      <div style={stylesAlmacens.acticonButtons}>
                        <button
                          style={{
                            ...stylesAlmacens.iconButton,
                            ...(buttonHoverStates[`edit-${item.id}`] ? stylesAlmacens.iconButtonHover : {}),
                          }}
                          onMouseEnter={() => handleButtonHover(`edit-${item.id}`, true)}
                          onMouseLeave={() => handleButtonHover(`edit-${item.id}`, false)}
                          onClick={() => handleEdit(item.id)}
                          title="Editar"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          style={{
                            ...stylesAlmacens.iconButton,
                            ...(buttonHoverStates[`delete-${item.id}`] ? stylesAlmacens.iconButtonDangerHover : {}),
                          }}
                          onMouseEnter={() => handleButtonHover(`delete-${item.id}`, true)}
                          onMouseLeave={() => handleButtonHover(`delete-${item.id}`, false)}
                          onClick={() => handleDelete(item.id)}
                          title="Eliminar"
                        >
                          <Trash size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={stylesAlmacens.paginationContainer}>
            <div style={stylesAlmacens.paginationInfo}>
              Mostrando {paginatedItems.length} de {filteredItems.length} servicios
            </div>

            <div style={stylesAlmacens.paginationControls}>
              <button
                disabled={pagination.currentPage === 1}
                onClick={() => handlePageChange(1)}
                style={{
                  ...stylesAlmacens.paginationButton,
                  ...(pagination.currentPage === 1 ? stylesAlmacens.paginationButtonDisabled : {}),
                }}
              >
                <ChevronsLeft size={16} />
              </button>
              <button
                disabled={pagination.currentPage === 1}
                onClick={() => handlePageChange(pagination.currentPage - 1)}
                style={{
                  ...stylesAlmacens.paginationButton,
                  ...(pagination.currentPage === 1 ? stylesAlmacens.paginationButtonDisabled : {}),
                }}
              >
                <ChevronLeft size={16} />
              </button>

              <span style={stylesAlmacens.paginationText}>
                {pagination.currentPage} de {totalPages}
              </span>

              <button
                disabled={pagination.currentPage === totalPages}
                onClick={() => handlePageChange(pagination.currentPage + 1)}
                style={{
                  ...stylesAlmacens.paginationButton,
                  ...(pagination.currentPage === totalPages ? stylesAlmacens.paginationButtonDisabled : {}),
                }}
              >
                <ChevronRight size={16} />
              </button>

              <button
                disabled={pagination.currentPage === totalPages}
                onClick={() => handlePageChange(totalPages)}
                style={{
                  ...stylesAlmacens.paginationButton,
                  ...(pagination.currentPage === totalPages ? stylesAlmacens.paginationButtonDisabled : {}),
                }}
              >
                <ChevronsRight size={16} />
              </button>

              <div style={styles.containerAlmacen}>
                <button
                  onClick={handleCancel}
                  onMouseEnter={() => setHoverStates(prev => ({ ...prev, cancel: true }))}
                  onMouseLeave={() => setHoverStates(prev => ({ ...prev, cancel: false }))}
                  style={{
                    ...styles.button,
                    ...styles.cancelButton,
                    ...(hoverStates.cancel ? styles.cancelButtonHover : {}),
                  }}
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default LabourList;