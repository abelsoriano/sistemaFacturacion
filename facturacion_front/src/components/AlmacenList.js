import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from "react-router-dom";
import { 
  Package, Plus, Search, Edit, Trash2, 
  ChevronLeft, ChevronRight, AlertCircle,
  X, Filter, ArrowUpDown
} from 'lucide-react';
import api from "../services/api";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import '../css/AlmacenList.css';

import {
  IconEdit,
  IconTrash
} from './Icons';


const AlmacenList = () => {
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'asc' });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  const navigate = useNavigate();

  const newItem = () => {
    navigate('/register-item');
  };

  const handleDelete = async (id, name) => {
    const result = await showConfirmationAlert(
      "¿Estás seguro?",
      `El artículo "${name}" será eliminado permanentemente.`
    );
    if (result.isConfirmed) {
      try {
        await api.delete(`/almacens/${id}/`);
        setItems(items.filter((item) => item.id !== id));
        showSuccessAlert("Eliminado", "El producto ha sido eliminado correctamente.");
      } catch (error) {
        showErrorAlert("Error", "No se pudo eliminar el producto.");
      }
    }
  };

  const handleCancel = () => {
    navigate('/home');
  };

  const handleEdit = (itemId) => {
    navigate(`/register-item/${itemId}`);
  };

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
      } catch (error) {
        console.error('Error al cargar datos', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  // Filtrar items
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.location.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesCategory = !categoryFilter ||
        (item.category_id && item.category_id.toString() === categoryFilter);

      return matchesSearch && matchesCategory;
    });
  }, [items, searchTerm, categoryFilter]);

  // Ordenar items
  const sortedItems = useMemo(() => {
    let sortableItems = [...filteredItems];
    if (sortConfig.key) {
      sortableItems.sort((a, b) => {
        let aValue = a[sortConfig.key];
        let bValue = b[sortConfig.key];
        
        if (sortConfig.key === 'stock') {
          aValue = Number(aValue);
          bValue = Number(bValue);
        }
        
        if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableItems;
  }, [filteredItems, sortConfig]);

  // Paginación
  const totalPages = Math.ceil(sortedItems.length / itemsPerPage);
  const paginatedItems = sortedItems.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const getStockClass = (stock) => {
    if (stock <= 3) return 'stock-critical';
    if (stock <= 10) return 'stock-warning';
    return 'stock-normal';
  };

  const clearFilters = () => {
    setSearchTerm('');
    setCategoryFilter('');
    setCurrentPage(1);
  };

  return (
    <div className="almacen-page">
      <div className="almacen-content">
        {/* Header */}
        <div className="page-header">
          <div className="header-title">
            <Package size={24} className="header-icon" />
            <div>
              <h1>Inventario de Almacén</h1>
              <p>Gestiona y controla todos los artículos de tu inventario</p>
            </div>
          </div>
          <div className="header-actions">
            <button onClick={handleCancel} className="btn-secondary">
              Volver al inicio
            </button>
            <button onClick={newItem} className="btn-primary">
              <Plus size={16} />
              Nuevo artículo
            </button>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="search-section">
          <div className="search-bar">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Buscar por nombre, descripción o ubicación..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button onClick={() => setSearchTerm('')} className="clear-btn">
                <X size={16} />
              </button>
            )}
          </div>

          <div className="filter-bar">
            <Filter size={18} />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">Todas las categorías</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id.toString()}>
                  {category.name}
                </option>
              ))}
            </select>
            
            {(searchTerm || categoryFilter) && (
              <button onClick={clearFilters} className="clear-filters">
                <X size={14} />
                Limpiar filtros
              </button>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="stats-row">
          <div className="stat-item">
            <span className="stat-label">Total artículos</span>
            <span className="stat-number">{filteredItems.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Stock crítico</span>
            <span className="stat-number critical">
              {filteredItems.filter(i => i.stock <= 3).length}
            </span>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Cargando inventario...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="empty-state">
            <Package size={48} />
            <h3>No se encontraron artículos</h3>
            <p>Intenta con otros filtros o agrega nuevos artículos</p>
            <button onClick={clearFilters} className="btn-secondary">
              Limpiar filtros
            </button>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th onClick={() => handleSort('name')} className="sortable">
                      Nombre
                      <ArrowUpDown size={14} />
                    </th>
                    <th>Descripción</th>
                    <th onClick={() => handleSort('category')} className="sortable">
                      Categoría
                      <ArrowUpDown size={14} />
                    </th>
                    <th onClick={() => handleSort('location')} className="sortable">
                      Ubicación
                      <ArrowUpDown size={14} />
                    </th>
                    <th onClick={() => handleSort('stock')} className="sortable">
                      Stock
                      <ArrowUpDown size={14} />
                    </th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedItems.map((item) => (
                    <tr key={item.id}>
                      <td className="item-name">
                        <Package size={16} />
                        {item.name}
                      </td>
                      <td className="description">{item.description}</td>
                      <td>
                        <span className="category-badge">{item.category}</span>
                      </td>
                      <td>{item.location}</td>
                      <td>
                        <span className={`stock-badge ${getStockClass(item.stock)}`}>
                          {item.stock <= 3 && <AlertCircle size={12} />}
                          {item.stock}
                        </span>
                      </td>
                      <td>
                        <div className="action-buttons">
                          <button
                          className="sl-act-btn sl-act-edit"
                            onClick={() => handleEdit(item.id)}
                            title="Editar"
                          >
                            <IconEdit />
                          </button>
                          <button 
                          className="sl-act-btn sl-act-del"
                            onClick={() => handleDelete(item.id, item.name)}
                            title="Eliminar"
                          >
                            <IconTrash />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="pagination">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft size={18} />
                </button>
                <span className="page-info">
                  Página {currentPage} de {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AlmacenList;