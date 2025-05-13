import React, { useState, useEffect } from 'react';

import {stylesAlmacens, styles, showConfirmationAlert, showSuccessAlert, showErrorAlert} from "../herpert";
import { ArrowUp, Edit, ArrowDown, Trash, ChevronsLeft, ChevronLeft, ChevronRight, ChevronsRight, FileX, Package, Plus, Search } from 'lucide-react';
import { useNavigate } from "react-router-dom";
import api from "../services/api"; 



// Componente principal para la lista de almacén
const AlmacenList = () => {

  const [items, setItems] = useState([]);
  const [filtereditems, setFiltereditems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'asc' });
  const [pagination, setPagination] = useState({
    currentPage: 1,
    itemsPerPage: 10,
    totalItems: 0
  });
  // const [deleteStatus, setDeleteStatus] = useState({ loading: false, error: null });
  const navigate = useNavigate();
  const [hoveredRow, setHoveredRow] = useState(null);
  const [buttonHoverStates, setButtonHoverStates] = useState({});
  const [hoverStates, setHoverStates] = useState({
      cancel: false,
      submit: false
    });

  const newItem = () => {
    navigate('/register-item');
  };

// Componente Modal para confirmar eliminación
  const handleDelete = async (id) => {
    const result = await showConfirmationAlert(
      "¿Estás seguro?",
      "Esta acción no se puede deshacer."
    );
  if (result.isConfirmed) {
    try {
      await api.delete(`/almacens/${id}/`);
      const updatedItem = items.filter((item) => item.id !== id);
      setItems(updatedItem);
      setFiltereditems(updatedItem);
      showSuccessAlert("Eliminado", "El producto ha sido eliminado.");
      } catch (error) {
          showErrorAlert("Error", "No se pudo eliminar el producto.");
        }
      }
  };

  const handleCancel = () => {
    navigate('/');
  };


  // Cargar datos del inventario y categorías
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [itemsResponse, categoriesResponse] = await Promise.all([
          api.get('almacens/'),
          api.get('categories/')
        ]);
        setItems(itemsResponse.data);
        setCategories(categoriesResponse.data);
        setPagination(prev => ({ ...prev, totalItems: itemsResponse.data.length }));
      } catch (error) {
        console.error('Error al cargar datos', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Manejo de la ordenación
  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  // Navegación a la página de edición
  const handleEdit = (itemId) => {
    navigate(`/register-item/${itemId}`);
  };


  // Filtrado de datos
  const filteredItems = items.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.location.toLowerCase().includes(searchTerm.toLowerCase());
  
    // Usar category_id directamente ya que ahora está disponible
    const matchesCategory = !categoryFilter || 
                           (item.category_id && item.category_id.toString() === categoryFilter);
  
    return matchesSearch && matchesCategory;
  });

  // Ordenación de datos
  const sortedItems = React.useMemo(() => {
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

  // Paginación
  const paginatedItems = React.useMemo(() => {
    const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
    return sortedItems.slice(startIndex, startIndex + pagination.itemsPerPage);
  }, [sortedItems, pagination.currentPage, pagination.itemsPerPage]);

  const totalPages = Math.ceil(filteredItems.length / pagination.itemsPerPage);

  const handlePageChange = (page) => {
    setPagination(prev => ({ ...prev, currentPage: page }));
  };

  // Determinar el estilo del stock basado en la cantidad
  const getStockStyle = (stock) => {
    if (stock <= 3) return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeLow };
    if (stock <= 10) return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeMedium };
    return { ...stylesAlmacens.badge, ...stylesAlmacens.badgeHigh };
  };

  // Renderización de los headers de las columnas
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

  // Hover handlers para botones
  const handleButtonHover = (id, isHovered) => {
    setButtonHoverStates(prev => ({ ...prev, [id]: isHovered }));
  };

  return (
    <div style={stylesAlmacens.container}>
      <div style={stylesAlmacens.header}>
        <div style={stylesAlmacens.headerTitle}>
          <span style={{ marginRight: "8px" }}>
            <Package size={20} />
          </span>
          <span>Inventario de Almacén</span>
        </div>
        <button
          style={{
            ...stylesAlmacens.button,
            ...stylesAlmacens.primaryButton,
            ...(buttonHoverStates["addNew"]
              ? stylesAlmacens.primaryButtonHover
              : {}),
          }}
          onMouseEnter={() => handleButtonHover("addNew", true)}
          onMouseLeave={() => handleButtonHover("addNew", false)}
          onClick={newItem}
        >
          <span style={{ marginRight: "8px" }}>
            <Plus size={16} />
          </span>
          Nuevo Artículo
        </button>
      </div>

      <div style={stylesAlmacens.searchFilterContainer}>
        <div style={stylesAlmacens.searchContainer}>
          <input
            type="text"
            placeholder="Buscar artículos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={stylesAlmacens.searchInput}
          />
          <div style={stylesAlmacens.searchIcon}>
            <Search size={16} />
          </div>
        </div>

        <div style={stylesAlmacens.filtersContainer}>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={stylesAlmacens.select}
          >
            <option value="">Todas las categorías</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id.toString()}>
                {category.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div style={stylesAlmacens.loadingContainer}>
          <div style={stylesAlmacens.spinner}></div>
          <p>Cargando inventario...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div style={stylesAlmacens.emptyState}>
          <FileX size={48} />
          <h3>No se encontraron artículos</h3>
          <p>
            Intenta cambiar los filtros o añade nuevos artículos al inventario.
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
                  {renderSortableHeader("category", "Categoría")}
                  {renderSortableHeader("location", "Ubicación")}
                  {renderSortableHeader("stock", "Stock")}
                  <th style={stylesAlmacens.tableHeader}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map((item) => (
                  <tr
                    key={item.id}
                    style={{
                      ...stylesAlmacens.tableRow,
                      ...(hoveredRow === item.id
                        ? stylesAlmacens.tableRowHover
                        : {}),
                    }}
                    onMouseEnter={() => setHoveredRow(item.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <td style={stylesAlmacens.tableCell}>
                      <div style={stylesAlmacens.itemName}>{item.name}</div>
                    </td>
                    <td style={stylesAlmacens.tableCell}>{item.description}</td>
                    <td style={stylesAlmacens.tableCell}>
                      <span style={stylesAlmacens.categoryBadge}>
                        {item.category}
                      </span>
                    </td>
                    <td style={stylesAlmacens.tableCell}>{item.location}</td>
                    <td style={stylesAlmacens.tableCell}>
                      <span style={getStockStyle(item.stock)}>
                        {item.stock}
                      </span>
                    </td>
                    <td style={stylesAlmacens.tableCell}>
                      <div style={stylesAlmacens.acticonButtons}>
                        <button
                          style={{
                            ...stylesAlmacens.iconButton,
                            ...(buttonHoverStates[`edit-${item.id}`]
                              ? stylesAlmacens.iconButtonHover
                              : {}),
                          }}
                          onMouseEnter={() =>
                            handleButtonHover(`edit-${item.id}`, true)
                          }
                          onMouseLeave={() =>
                            handleButtonHover(`edit-${item.id}`, false)
                          }
                          onClick={() => handleEdit(item.id)}
                          title="Editar"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          style={{
                            ...stylesAlmacens.iconButton,
                            ...(buttonHoverStates[`delete-${item.id}`]
                              ? stylesAlmacens.iconButtonDangerHover
                              : {}),
                          }}
                          onMouseEnter={() =>
                            handleButtonHover(`delete-${item.id}`, true)
                          }
                          onMouseLeave={() =>
                            handleButtonHover(`delete-${item.id}`, false)
                          }
                          onClick={() => handleDelete(item.id, item.name)}
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
              Mostrando {paginatedItems.length} de {filteredItems.length}{" "}
              artículos
            </div>

            <div style={stylesAlmacens.paginationControls}>
              <button
                disabled={pagination.currentPage === 1}
                onClick={() => handlePageChange(1)}
                style={{
                  ...stylesAlmacens.paginationButton,
                  ...(pagination.currentPage === 1
                    ? stylesAlmacens.paginationButtonDisabled
                    : {}),
                }}
              >
                <ChevronsLeft size={16} />
              </button>
              <button
                disabled={pagination.currentPage === 1}
                onClick={() => handlePageChange(pagination.currentPage - 1)}
                style={{
                  ...stylesAlmacens.paginationButton,
                  ...(pagination.currentPage === 1
                    ? stylesAlmacens.paginationButtonDisabled
                    : {}),
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
                  ...(pagination.currentPage === totalPages
                    ? stylesAlmacens.paginationButtonDisabled
                    : {}),
                }}
              >
                <ChevronRight size={16} />
              </button>

              <button
                disabled={pagination.currentPage === totalPages}
                onClick={() => handlePageChange(totalPages)}
                style={{
                  ...stylesAlmacens.paginationButton,
                  ...(pagination.currentPage === totalPages
                    ? stylesAlmacens.paginationButtonDisabled
                    : {}),
                }}
              >
                <ChevronsRight size={16} />
              </button>

              <div style={styles.containerAlmacen}>
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
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default AlmacenList;