import React, { useState, useEffect } from "react";
import api from "../services/api";
import { useNavigate } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import {
  FaPlus, FaSearch,
  FaFolder, FaTag, FaTimes,
  FaInfoCircle
} from 'react-icons/fa';
import '../css/Category.css';

import {
  IconEdit,
  IconTrash
} from './Icons';

/* ─── CSS Moderno y Responsive ──────────────────────────────────────────── */
const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap');

  .cat-root {
    --bg-page: #f8fafc;
    --surface: #ffffff;
    --surface-hover: #f1f5f9;
    --border: #e2e8f0;
    --border-dark: #cbd5e1;
    --text: #0f172a;
    --text-muted: #475569;
    --text-faint: #94a3b8;
    --primary: #3b82f6;
    --primary-dark: #2563eb;
    --primary-light: #eff6ff;
    --success: #10b981;
    --success-light: #d1fae5;
    --danger: #ef4444;
    --danger-light: #fee2e2;
    --warning: #f59e0b;
    --warning-light: #fed7aa;
    --purple: #8b5cf6;
    --purple-light: #ede9fe;
    --radius-sm: 0.5rem;
    --radius-md: 0.75rem;
    --radius-lg: 1rem;
    --shadow: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05);
    --font: 'Inter', system-ui, -apple-system, sans-serif;
    --mono: 'SF Mono', 'Monaco', monospace;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  .cat-root {
    font-family: var(--font);
    background: var(--bg-page);
    min-height: 100vh;
    color: var(--text);
  }

  /* Header */
  .cat-header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0.75rem 1rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    position: sticky;
    top: 0;
    z-index: 50;
    backdrop-filter: blur(8px);
    background: rgba(255,255,255,0.95);
  }

  @media (min-width: 768px) {
    .cat-header {
      padding: 0 1.5rem;
      height: 64px;
      flex-wrap: nowrap;
    }
  }

  .cat-header-title {
    font-size: 0.875rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
  }

  @media (min-width: 640px) {
    .cat-header-title {
      font-size: 1rem;
    }
  }

  .cat-header-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  /* Main Content */
  .cat-body {
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  @media (min-width: 768px) {
    .cat-body {
      padding: 1.5rem;
    }
  }

  /* Stats Card */
  .cat-stats {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .cat-stats-info {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .cat-stats-icon {
    width: 3rem;
    height: 3rem;
    border-radius: var(--radius-md);
    background: var(--primary-light);
    color: var(--primary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
  }

  .cat-stats-text h3 {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.2;
  }

  .cat-stats-text p {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin: 0;
  }

  /* Filter Card */
  .cat-filter-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    margin-bottom: 1rem;
    overflow: hidden;
  }

  .cat-filter-header {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    background: var(--surface-hover);
  }

  .cat-filter-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-muted);
  }

  .cat-filter-body {
    padding: 1rem;
  }

  .cat-search-wrapper {
    position: relative;
  }

  .cat-search-icon {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-faint);
    pointer-events: none;
  }

  .cat-search-input {
    width: 100%;
    padding: 0.625rem 0.75rem 0.625rem 2.25rem;
    font-size: 0.875rem;
    border: 1.5px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface);
    transition: all 0.2s ease;
  }

  .cat-search-input:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-light);
  }

  /* Table Card */
  .cat-table-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow);
  }

  .cat-table-header {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    background: var(--surface-hover);
  }

  .cat-table-title {
    font-size: 0.8125rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--text-muted);
  }

  .cat-badge {
    font-size: 0.6875rem;
    font-weight: 600;
    padding: 0.1875rem 0.5rem;
    border-radius: 9999px;
    background: var(--surface-2);
    color: var(--text-faint);
  }

  /* Table Responsive */
  .cat-table-wrapper {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .cat-table {
    width: 100%;
    border-collapse: collapse;
    min-width: 500px;
  }

  .cat-table th {
    text-align: left;
    padding: 0.875rem 1rem;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-faint);
    background: var(--surface-hover);
    border-bottom: 1px solid var(--border);
  }

  .cat-table td {
    padding: 0.875rem 1rem;
    border-bottom: 1px solid var(--border);
    font-size: 0.8125rem;
  }

  .cat-table tbody tr:hover td {
    background: var(--surface-hover);
  }

  /* Category Name Cell */
  .cat-name-cell {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .cat-icon {
    width: 2.25rem;
    height: 2.25rem;
    border-radius: var(--radius-md);
    background: var(--primary-light);
    color: var(--primary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
  }

  .cat-name {
    font-weight: 600;
    font-size: 0.875rem;
  }

  /* Action Buttons */
  .cat-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .cat-action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .cat-action-btn:hover {
    transform: translateY(-1px);
  }

  .btn-edit {
    background: var(--primary-light);
    color: var(--primary);
  }
  .btn-edit:hover {
    background: var(--primary);
    color: white;
  }

  .btn-delete {
    background: var(--danger-light);
    color: var(--danger);
  }
  .btn-delete:hover {
    background: var(--danger);
    color: white;
  }

  /* Main Buttons */
  .cat-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    font-size: 0.8125rem;
    font-weight: 500;
    border-radius: var(--radius-sm);
    border: 1.5px solid transparent;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: var(--font);
    text-decoration: none;
  }

  .cat-btn-primary {
    background: var(--primary);
    color: white;
  }
  .cat-btn-primary:hover {
    background: var(--primary-dark);
    transform: translateY(-1px);
  }

  .cat-btn-secondary {
    border-color: var(--border);
    background: var(--surface);
    color: var(--text-muted);
  }
  .cat-btn-secondary:hover {
    background: var(--surface-hover);
    border-color: var(--border-dark);
  }

  .cat-btn-sm {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }

  /* Empty State */
  .cat-empty {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-faint);
  }
  .cat-empty svg {
    opacity: 0.3;
    margin-bottom: 0.75rem;
  }

  /* Loading State */
  .cat-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    gap: 1rem;
  }

  .cat-spinner {
    width: 2.5rem;
    height: 2.5rem;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ID Badge */
  .cat-id-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    padding: 0.25rem 0.5rem;
    background: var(--surface-hover);
    border-radius: var(--radius-sm);
    font-family: var(--mono);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
  }
`;

function InjectStyles() {
  useEffect(() => {
    const id = "category-list-styles";
    if (!document.getElementById(id)) {
      const style = document.createElement("style");
      style.id = id;
      style.textContent = STYLES;
      document.head.appendChild(style);
    }
  }, []);
  return null;
}

/* ─── Componente Principal ─────────────────────────────────────────────── */
const CategoryList = () => {
  const [categories, setCategories] = useState([]);
  const [filteredCategories, setFilteredCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get('categories/');
      setCategories(response.data);
      setFilteredCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
      setError(error);
      toast.error('Error al cargar las categorías');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = (id) => {
    navigate(`/categoriesForm/${id}`);
  };

  const handleDelete = async (id, name) => {
    const result = await Swal.fire({
      title: '¿Eliminar categoría?',
      html: `¿Estás seguro de eliminar la categoría <strong>${name}</strong>?<br/>
                   <small>Esta acción no se puede deshacer.</small>`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#6b7280',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (result.isConfirmed) {
      try {
        await api.delete(`categories/${id}/`);
        const updatedCategories = categories.filter(cat => cat.id !== id);
        setCategories(updatedCategories);
        setFilteredCategories(updatedCategories);
        toast.success('Categoría eliminada exitosamente');
      } catch (error) {
        console.error('Error deleting category:', error);
        if (error.response?.status === 409) {
          toast.error('No se puede eliminar la categoría porque tiene productos asociados');
        } else {
          toast.error('Error al eliminar la categoría');
        }
      }
    }
  };

  const handleSearch = (event) => {
    const term = event.target.value.toLowerCase();
    setSearchTerm(term);

    if (term === '') {
      setFilteredCategories(categories);
    } else {
      const filtered = categories.filter(category =>
        category.name.toLowerCase().includes(term)
      );
      setFilteredCategories(filtered);
    }
  };

  const clearSearch = () => {
    setSearchTerm('');
    setFilteredCategories(categories);
  };

  const getCategoryColor = (name) => {
    const colors = [
      { bg: '#eff6ff', text: '#3b82f6' },
      { bg: '#d1fae5', text: '#10b981' },
      { bg: '#fed7aa', text: '#f59e0b' },
      { bg: '#ede9fe', text: '#8b5cf6' },
      { bg: '#cffafe', text: '#06b6d4' },
    ];
    const index = name.length % colors.length;
    return colors[index];
  };

  if (isLoading) {
    return (
      <div className="cat-root">
        <InjectStyles />
        <div className="cat-loading">
          <div className="cat-spinner" />
          <span style={{ color: 'var(--text-muted)' }}>Cargando categorías...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="cat-root">
      <InjectStyles />
      <Toaster position="top-right" />

      {/* Header */}
      <header className="cat-header cat-page-header">
        <div className="cat-header-title">
          <span className="cat-title-icon"><FaFolder size={16} /></span>
          <span>
            <strong>Gestión de categorías</strong>
            <small>Organiza productos y artículos por familia comercial.</small>
          </span>
          <span className="cat-badge">{categories.length}</span>
        </div>

        <div className="cat-header-actions">
          <button
            className="cat-btn cat-btn-primary cat-btn-sm"
            onClick={() => navigate('/categoriesForm')}
          >
            <FaPlus size={11} /> Nueva Categoría
          </button>
        </div>
      </header>

      <div className="cat-body">
        {/* Stats Card */}
        <div className="cat-stats">
          <div className="cat-stats-info">
            <div className="cat-stats-icon">
              <FaFolder size={24} />
            </div>
            <div className="cat-stats-text">
              <h3>{categories.length}</h3>
              <p>Categorías registradas</p>
            </div>
          </div>
          {filteredCategories.length !== categories.length && (
            <div className="cat-stats-info">
              <div className="cat-stats-icon" style={{ background: 'var(--success-light)', color: 'var(--success)' }}>
                <FaSearch size={24} />
              </div>
              <div className="cat-stats-text">
                <h3>{filteredCategories.length}</h3>
                <p>Resultados de búsqueda</p>
              </div>
            </div>
          )}
        </div>

        {/* Search Bar */}
        <div className="cat-filter-card">
          <div className="cat-filter-header">
            <div className="cat-filter-title">
              <FaSearch size={11} /> Buscar categoría
              {searchTerm && (
                <span className="cat-badge" style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
                  activo
                </span>
              )}
            </div>
            {searchTerm && (
              <button className="cat-btn cat-btn-secondary cat-btn-sm" onClick={clearSearch}>
                <FaTimes size={10} /> Limpiar
              </button>
            )}
          </div>
          <div className="cat-filter-body">
            <div className="cat-search-wrapper">
              <FaSearch className="cat-search-icon" />
              <input
                type="text"
                className="cat-search-input"
                placeholder="Buscar por nombre de categoría..."
                value={searchTerm}
                onChange={handleSearch}
                autoFocus
              />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="cat-table-card">
          <div className="cat-table-header">
            <div className="cat-table-title">
              <FaTag size={12} /> Listado de Categorías
              <span className="cat-badge">{filteredCategories.length} categorías</span>
            </div>
          </div>

          <div className="cat-table-wrapper">
            <table className="cat-table">
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>ID</th>
                  <th>Nombre</th>
                  <th style={{ width: '200px' }} className="text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredCategories.length === 0 ? (
                  <tr>
                    <td colSpan="3">
                      <div className="cat-empty">
                        <FaFolder size={48} />
                        <p>
                          {searchTerm
                            ? "No hay categorías que coincidan con la búsqueda"
                            : "No hay categorías registradas"}
                        </p>
                        {searchTerm && (
                          <button className="cat-btn cat-btn-secondary cat-btn-sm" onClick={clearSearch}>
                            Limpiar búsqueda
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredCategories.map((category) => {
                    const colors = getCategoryColor(category.name);
                    return (
                      <tr key={category.id}>
                        <td data-label="ID">
                          <span className="cat-id-badge">#{category.id}</span>
                        </td>
                        <td data-label="Nombre">
                          <div className="cat-name-cell">
                            <div className="cat-icon" style={{ background: colors.bg, color: colors.text }}>
                              <FaTag size={14} />
                            </div>
                            <span className="cat-name">{category.name}</span>
                          </div>
                        </td>
                        <td className="text-center" data-label="Acciones">
                          <div className="cat-actions">
                            <button className="sl-act-btn sl-act-edit"
                              onClick={() => handleEdit(category.id)}
                              title="Editar categoría"
                            >
                              <IconEdit />
                            </button>
                            <button className="sl-act-btn sl-act-del"
                              onClick={() => handleDelete(category.id, category.name)}
                              title="Eliminar categoría"
                            >
                              <IconTrash />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Info Card */}
        <div className="cat-info-card">
          <FaInfoCircle size={14} />
          <span><strong>Información:</strong> Las categorías ayudan a organizar tus productos. No se pueden eliminar categorías que tengan productos asociados.</span>
        </div>
      </div>
    </div>
  );
};

export default CategoryList;
