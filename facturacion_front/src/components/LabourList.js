import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowUp, ArrowDown, ChevronsLeft, ChevronLeft,
  ChevronRight, ChevronsRight, FileX, Package, Plus, Search,
  CreditCard, DollarSign, X, CheckCircle, Clock, AlertCircle, Wallet
} from 'lucide-react';
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import '../css/SalesList.css';
import '../css/Labour.css';
import {
  IconEdit,
  IconTrash
} from './Icons';

// ── Badge de estado de pago ──────────────────────────────────────────
const BadgeEstado = ({ estado }) => {
  const config = {
    pagado: { cls: 'lab-badge-success', label: 'Pagado', Icon: CheckCircle },
    parcial: { cls: 'lab-badge-warning', label: 'Parcial', Icon: Clock },
    pendiente: { cls: 'lab-badge-danger', label: 'Pendiente', Icon: AlertCircle },
  };
  const c = config[estado] || config.pendiente;
  return (
    <span className={`lab-badge ${c.cls}`}>
      <c.Icon size={11} />
      {c.label}
    </span>
  );
};


// ── Badge modalidad ──────────────────────────────────────────────────
const BadgeModalidad = ({ modalidad }) => (
  <span className={`lab-badge ${modalidad === 'credito' ? 'lab-badge-info' : 'lab-badge-success'}`}>
    {modalidad === 'credito' ? <CreditCard size={11} /> : <DollarSign size={11} />}
    {modalidad === 'credito' ? 'Crédito' : 'Contado'}
  </span>
);

// ── Modal de Abonos ──────────────────────────────────────────────────
const ModalAbonos = ({ servicio, onClose, onAbonoRegistrado }) => {
  const [monto, setMonto] = useState('');
  const [notas, setNotas] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  const saldo = parseFloat(servicio.saldo_pendiente || 0);

  const handlePagarCompleto = async () => {
    setGuardando(true);
    setError('');
    try {
      await api.post(`servicios-mano-obra/${servicio.id}/pagar-completo/`);
      showSuccessAlert("Pago registrado", "El servicio ha sido saldado completamente.");
      onAbonoRegistrado();
      onClose();
    } catch (err) {
      setError("Error al registrar el pago completo.");
    } finally {
      setGuardando(false);
    }
  };

  const handleAbono = async () => {
    setError('');
    const montoNum = parseFloat(monto);
    if (!monto || isNaN(montoNum) || montoNum <= 0) {
      setError("Ingrese un monto válido mayor a cero.");
      return;
    }
    if (montoNum > saldo) {
      setError(`El monto no puede superar el saldo pendiente ($${saldo.toFixed(2)}).`);
      return;
    }
    setGuardando(true);
    try {
      await api.post("abonos/", {
        servicio: servicio.id,
        monto: montoNum,
        notas: notas || ''
      });
      showSuccessAlert("Abono registrado", `Se registró un abono de $${montoNum.toFixed(2)}.`);
      onAbonoRegistrado();
      onClose();
    } catch (err) {
      const data = err.response?.data;
      if (typeof data === 'object') {
        const msgs = Object.values(data).flat().join(' ');
        setError(msgs || "Error al registrar el abono.");
      } else {
        setError("Error al registrar el abono.");
      }
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="lab-modal-overlay">
      <div className="lab-modal">
        <div className="lab-modal-header">
          <div>
            <h3>Registrar abono</h3>
            <p>{servicio.nombre_persona}</p>
          </div>
          <button onClick={onClose} className="lab-modal-close">
            <X size={18} />
          </button>
        </div>

        <div className="lab-modal-body">
          <div className="lab-summary-grid">
            {[
              { label: 'Total', value: `$${parseFloat(servicio.precio_total).toFixed(2)}` },
              { label: 'Abonado', value: `$${parseFloat(servicio.total_abonado || 0).toFixed(2)}` },
              { label: 'Pendiente', value: `$${saldo.toFixed(2)}` },
            ].map(({ label, value }) => (
              <div key={label} className="lab-summary-tile">
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>

          {servicio.abonos && servicio.abonos.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p className="lab-section-title" style={{ marginBottom: 8 }}>Historial</p>
              <div className="lab-history">
                {servicio.abonos.map((abono) => (
                  <div key={abono.id} className="lab-history-row">
                    <span>
                      {new Date(abono.fecha_abono).toLocaleDateString('es-CO')}
                      {abono.notas && ` · ${abono.notas}`}
                    </span>
                    <strong style={{ color: 'var(--lab-success)' }}>
                      +${parseFloat(abono.monto).toFixed(2)}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          )}

          {saldo > 0 ? (
            <div className="lab-form">
              <label>
                Monto del abono
              <input
                type="number"
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
                placeholder={`Máximo $${saldo.toFixed(2)}`}
                min="0.01"
                step="0.01"
              />
              </label>
              <label>
                Notas (opcional)
              <input
                type="text"
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Ej: Pago en efectivo"
              />
              </label>

              {error && (
                <div className="lab-error">
                  <AlertCircle size={14} /> {error}
                </div>
              )}

              <div className="lab-actions-row">
              <button
                onClick={handleAbono}
                disabled={guardando}
                className="lab-btn lab-btn-primary"
              >
                {guardando ? 'Guardando...' : 'Registrar abono'}
              </button>
              <button
                onClick={handlePagarCompleto}
                disabled={guardando}
                className="lab-btn lab-btn-success"
              >
                Pagar todo (${saldo.toFixed(2)})
              </button>
            </div>
            </div>
          ) : (
          <div className="lab-paid-state">
            <CheckCircle size={24} style={{ marginBottom: '6px' }} />
            <p style={{ margin: 0, fontWeight: 500 }}>Servicio completamente pagado</p>
          </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Componente principal ─────────────────────────────────────────────
const LabourList = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('todos');
  const [sortConfig, setSortConfig] = useState({ key: 'nombre_persona', direction: 'asc' });
  const [pagination, setPagination] = useState({ currentPage: 1, itemsPerPage: 10 });
  const [servicioAbono, setServicioAbono] = useState(null); // modal

  const navigate = useNavigate();

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('servicios-mano-obra/');
      setItems(response.data);
    } catch (error) {
      console.error('Error al cargar datos', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleDelete = async (id) => {
    const result = await showConfirmationAlert("¿Estás seguro?", "Esta acción no se puede deshacer.");
    if (result.isConfirmed) {
      try {
        await api.delete(`servicios-mano-obra/${id}/`);
        setItems(prev => prev.filter(item => item.id !== id));
        showSuccessAlert("Eliminado", "El servicio ha sido eliminado.");
      } catch {
        showErrorAlert("Error", "No se pudo eliminar el servicio.");
      }
    }
  };

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // Filtrado + búsqueda + sort + paginación
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      const matchSearch =
        item.nombre_persona?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.descripcion?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.factura_asociada?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchEstado = filtroEstado === 'todos' || item.estado_pago === filtroEstado;
      return matchSearch && matchEstado;
    });
  }, [items, searchTerm, filtroEstado]);

  const sortedItems = useMemo(() => {
    return [...filteredItems].sort((a, b) => {
      const aVal = a[sortConfig.key] ?? '';
      const bVal = b[sortConfig.key] ?? '';
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredItems, sortConfig]);

  const totalPages = Math.ceil(sortedItems.length / pagination.itemsPerPage);
  const paginatedItems = useMemo(() => {
    const start = (pagination.currentPage - 1) * pagination.itemsPerPage;
    return sortedItems.slice(start, start + pagination.itemsPerPage);
  }, [sortedItems, pagination]);

  // Métricas resumen
  const metricas = useMemo(() => {
    const total = items.reduce((s, i) => s + parseFloat(i.precio_total || 0), 0);
    const cobrado = items.reduce((s, i) => s + parseFloat(i.total_abonado || 0), 0);
    const pendiente = total - cobrado;
    const credito = items.filter(i => i.modalidad_pago === 'credito').length;
    const pendientes = items.filter(i => i.estado_pago === 'pendiente').length;
    const pagados = items.filter(i => i.estado_pago === 'pagado').length;
    return { total, cobrado, pendiente, credito, pendientes, pagados };
  }, [items]);

  const renderSortIcon = (key) => {
    if (sortConfig.key !== key) return null;
    return sortConfig.direction === 'asc' ? <ArrowUp size={13} /> : <ArrowDown size={13} />;
  };

  return (
    <div className="lab-root">
      <div className="lab-shell">

      {/* Modal abonos */}
      {servicioAbono && (
        <ModalAbonos
          servicio={servicioAbono}
          onClose={() => setServicioAbono(null)}
          onAbonoRegistrado={fetchData}
        />
      )}

      {/* Header */}
      <div className="lab-header">
        <div>
          <h2>
            <Package size={22} /> Mano de obra
          </h2>
          <p>{items.length} servicios registrados con control de abonos y saldos.</p>
        </div>
        <div className="lab-actions-row">
          <button
            onClick={() => navigate('/home')}
            className="lab-btn lab-btn-outline"
          >
            Volver
          </button>

          <button
            onClick={() => navigate('/register-labour')}
            className="lab-btn lab-btn-primary"
          >
            <Plus size={16} /> Nuevo servicio
          </button>
        </div>
      </div>

      {/* Tarjetas métricas */}
      <div className="lab-stats">
        {[
          { label: 'Total servicios', value: items.length, icon: Package, color: 'var(--lab-text)' },
          { label: 'Pendientes', value: metricas.pendientes, icon: AlertCircle, color: 'var(--lab-danger)' },
          { label: 'Pagados', value: metricas.pagados, icon: CheckCircle, color: 'var(--lab-success)' },
          { label: 'Monto pendiente', value: `$${metricas.pendiente.toFixed(2)}`, icon: CreditCard, color: 'var(--lab-primary)' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="lab-stat-card">
            <div className="lab-stat-top">
              <span>{label}</span>
              <Icon size={15} style={{ color }} />
            </div>
            <strong style={{ color }}>{value}</strong>
          </div>
        ))}
      </div>

      {/* Búsqueda y filtros */}
      <div className="lab-card lab-filter-card">
        <div className="lab-search">
          <input
            type="text"
            placeholder="Buscar por nombre, descripción o factura..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setPagination(p => ({ ...p, currentPage: 1 })); }}
          />
          <Search size={15} />
        </div>
        <div className="lab-filter-pills">
          {['todos', 'pendiente', 'parcial', 'pagado'].map(estado => (
            <button
              key={estado}
              onClick={() => { setFiltroEstado(estado); setPagination(p => ({ ...p, currentPage: 1 })); }}
              className={`lab-pill ${filtroEstado === estado ? 'active' : ''}`}
            >
              {{ todos: 'Todos', pendiente: 'Pendientes', parcial: 'Parciales', pagado: 'Pagados' }[estado]}
            </button>
          ))}
        </div>
      </div>

      {/* Tabla */}
      {loading ? (
        <div className="lab-card lab-loading">
          <div className="lab-spinner"></div>
          <p>Cargando servicios...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="lab-card lab-empty">
          <FileX size={48} />
          <h3>No se encontraron servicios</h3>
          <p>Intenta cambiar los filtros o añade un nuevo servicio.</p>
        </div>
      ) : (
        <>
          <div className="lab-card lab-table-card">
            <div className="lab-table-wrap">
            <table className="lab-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('nombre_persona')}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>Nombre {renderSortIcon('nombre_persona')}</span>
                  </th>
                  <th>Descripción</th>
                  <th onClick={() => handleSort('precio_total')}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>Precio {renderSortIcon('precio_total')}</span>
                  </th>
                  <th>Abonado</th>
                  <th>Pendiente</th>
                  <th>Modalidad</th>
                  <th>Estado</th>
                  <th>Factura</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map((item) => (
                  <tr key={item.id}>
                    <td data-label="Nombre" style={{ fontWeight: 750 }}>
                      {item.nombre_persona}
                    </td>
                    <td data-label="Descripción" className="lab-muted" style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.descripcion || '—'}
                    </td>
                    <td data-label="Precio" className="lab-money">
                      ${parseFloat(item.precio_total).toFixed(2)}
                    </td>
                    <td data-label="Abonado" className="lab-money" style={{ color: 'var(--lab-success)' }}>
                      ${parseFloat(item.total_abonado || 0).toFixed(2)}
                    </td>
                    <td data-label="Pendiente" className="lab-money" style={{ color: parseFloat(item.saldo_pendiente) > 0 ? 'var(--lab-danger)' : 'var(--lab-success)' }}>
                      ${parseFloat(item.saldo_pendiente || 0).toFixed(2)}
                    </td>
                    <td data-label="Modalidad">
                      <BadgeModalidad modalidad={item.modalidad_pago} />
                    </td>
                    <td data-label="Estado">
                      <BadgeEstado estado={item.estado_pago} />
                    </td>
                    <td data-label="Factura" className="lab-muted">
                      {item.factura_asociada || '—'}
                    </td>
                    <td data-label="Acciones">
                      <div className="lab-action-buttons">
                        {/* Abono (solo crédito no pagado) */}
                        <div className="lab-action-group">
                          {item.modalidad_pago === 'credito' && item.estado_pago !== 'pagado' && (
                            <button
                              onClick={() => setServicioAbono(item)}
                              title="Registrar abono"
                              className="lab-btn lab-btn-success"
                            >
                              <Wallet size={13} /> Abonar
                            </button>
                          )}
                          <button className="lab-icon-btn"
                            onClick={() => navigate(`/register-labour/${item.id}`)}
                            title="Editar"
                          >
                             <IconEdit />
                          </button>
                        </div>
                        <div className="lab-action-group">
                          <button className="lab-icon-btn"
                            onClick={() => handleDelete(item.id)}
                            title="Eliminar"
                          >
                             <IconTrash />
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>

          {/* Paginación */}
          <div className="lab-pagination">
            <span className="lab-muted">
              Mostrando {paginatedItems.length} de {filteredItems.length} servicios
            </span>
            <div className="lab-page-buttons">
              {[
                { icon: ChevronsLeft, action: () => setPagination(p => ({ ...p, currentPage: 1 })), disabled: pagination.currentPage === 1 },
                { icon: ChevronLeft, action: () => setPagination(p => ({ ...p, currentPage: p.currentPage - 1 })), disabled: pagination.currentPage === 1 },
                { icon: ChevronRight, action: () => setPagination(p => ({ ...p, currentPage: p.currentPage + 1 })), disabled: pagination.currentPage === totalPages },
                { icon: ChevronsRight, action: () => setPagination(p => ({ ...p, currentPage: totalPages })), disabled: pagination.currentPage === totalPages },
              ].map(({ icon: Icon, action, disabled }, i) => (
                <button key={i} onClick={action} disabled={disabled} className="lab-icon-btn">
                  <Icon size={15} />
                </button>
              ))}
              <span className="lab-muted" style={{ padding: '0 8px' }}>
                {pagination.currentPage} / {totalPages}
              </span>
            </div>
          </div>
        </>
      )}
      </div>
    </div>
  );
};

export default LabourList;
