import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowUp, ArrowDown, Edit, Trash, ChevronsLeft, ChevronLeft,
  ChevronRight, ChevronsRight, FileX, Package, Plus, Search,
  CreditCard, DollarSign, X, CheckCircle, Clock, AlertCircle, Wallet
} from 'lucide-react';
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { stylesAlmacens, styles, showConfirmationAlert, showSuccessAlert, showErrorAlert } from "../herpert";
import '../css/SalesList.css';
import {
  IconEdit,
  IconTrash
} from './Icons';

// ── Badge de estado de pago ──────────────────────────────────────────
const BadgeEstado = ({ estado }) => {
  const config = {
    pagado: { bg: '#f0fdf4', color: '#15803d', border: '#bbf7d0', label: 'Pagado', Icon: CheckCircle },
    parcial: { bg: '#fffbeb', color: '#b45309', border: '#fde68a', label: 'Parcial', Icon: Clock },
    pendiente: { bg: '#fef2f2', color: '#dc2626', border: '#fecaca', label: 'Pendiente', Icon: AlertCircle },
  };
  const c = config[estado] || config.pendiente;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      padding: '3px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: 500,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`
    }}>
      <c.Icon size={11} />
      {c.label}
    </span>
  );
};


// ── Badge modalidad ──────────────────────────────────────────────────
const BadgeModalidad = ({ modalidad }) => (
  <span style={{
    display: 'inline-flex', alignItems: 'center', gap: '4px',
    padding: '3px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: 500,
    background: modalidad === 'credito' ? '#eff6ff' : '#f0fdf4',
    color: modalidad === 'credito' ? '#1d4ed8' : '#15803d',
    border: `1px solid ${modalidad === 'credito' ? '#bfdbfe' : '#bbf7d0'}`
  }}>
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
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
    }}>
      <div style={{
        background: 'var(--color-background-primary, #fff)',
        borderRadius: '16px', padding: '28px', width: '100%', maxWidth: '460px',
        border: '0.5px solid var(--color-border-tertiary)', boxShadow: '0 8px 32px rgba(0,0,0,0.12)'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 500 }}>Registrar abono</h3>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              {servicio.nombre_persona}
            </p>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-text-secondary)', padding: '4px'
          }}>
            <X size={18} />
          </button>
        </div>

        {/* Resumen financiero */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '20px'
        }}>
          {[
            { label: 'Total', value: `$${parseFloat(servicio.precio_total).toFixed(2)}`, color: '#374151' },
            { label: 'Abonado', value: `$${parseFloat(servicio.total_abonado || 0).toFixed(2)}`, color: '#15803d' },
            { label: 'Pendiente', value: `$${saldo.toFixed(2)}`, color: '#dc2626' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              background: 'var(--color-background-secondary, #f9fafb)',
              borderRadius: '10px', padding: '10px 12px', textAlign: 'center'
            }}>
              <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>{label}</div>
              <div style={{ fontSize: '15px', fontWeight: 500, color }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Historial abonos */}
        {servicio.abonos && servicio.abonos.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <p style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-text-secondary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Historial
            </p>
            <div style={{ maxHeight: '120px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {servicio.abonos.map((abono) => (
                <div key={abono.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 12px', borderRadius: '8px',
                  background: 'var(--color-background-secondary, #f9fafb)',
                  fontSize: '13px'
                }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>
                    {new Date(abono.fecha_abono).toLocaleDateString('es-CO')}
                    {abono.notas && ` · ${abono.notas}`}
                  </span>
                  <span style={{ fontWeight: 500, color: '#15803d' }}>
                    +${parseFloat(abono.monto).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Formulario */}
        {saldo > 0 ? (
          <>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                Monto del abono
              </label>
              <input
                type="number"
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
                placeholder={`Máximo $${saldo.toFixed(2)}`}
                min="0.01"
                step="0.01"
                style={{ ...styles.input, width: '100%' }}
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                Notas (opcional)
              </label>
              <input
                type="text"
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Ej: Pago en efectivo"
                style={{ ...styles.input, width: '100%' }}
              />
            </div>

            {error && (
              <div style={{
                background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px',
                padding: '10px 12px', fontSize: '13px', color: '#dc2626', marginBottom: '14px',
                display: 'flex', alignItems: 'center', gap: '6px'
              }}>
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={handleAbono}
                disabled={guardando}
                style={{
                  flex: 1, padding: '10px', borderRadius: '10px', border: 'none',
                  background: '#1d4ed8', color: '#fff', fontWeight: 500, fontSize: '14px',
                  cursor: guardando ? 'not-allowed' : 'pointer', opacity: guardando ? 0.7 : 1
                }}
              >
                {guardando ? 'Guardando...' : 'Registrar abono'}
              </button>
              <button
                onClick={handlePagarCompleto}
                disabled={guardando}
                style={{
                  flex: 1, padding: '10px', borderRadius: '10px',
                  border: '1px solid #bbf7d0', background: '#f0fdf4',
                  color: '#15803d', fontWeight: 500, fontSize: '14px',
                  cursor: guardando ? 'not-allowed' : 'pointer', opacity: guardando ? 0.7 : 1
                }}
              >
                Pagar todo (${saldo.toFixed(2)})
              </button>
            </div>
          </>
        ) : (
          <div style={{
            textAlign: 'center', padding: '16px',
            background: '#f0fdf4', borderRadius: '10px', color: '#15803d'
          }}>
            <CheckCircle size={24} style={{ marginBottom: '6px' }} />
            <p style={{ margin: 0, fontWeight: 500 }}>Servicio completamente pagado</p>
          </div>
        )}
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
  const [hoveredRow, setHoveredRow] = useState(null);
  const [buttonHoverStates, setButtonHoverStates] = useState({});
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

  const handleButtonHover = (id, isHovered) => {
    setButtonHoverStates(prev => ({ ...prev, [id]: isHovered }));
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
    return { total, cobrado, pendiente, credito };
  }, [items]);

  const renderSortIcon = (key) => {
    if (sortConfig.key !== key) return null;
    return sortConfig.direction === 'asc' ? <ArrowUp size={13} /> : <ArrowDown size={13} />;
  };

  const thStyle = (key) => ({
    ...stylesAlmacens.tableHeader,
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap'
  });

  return (
    <div style={{ ...stylesAlmacens.container, maxWidth: '1100px' }}>

      {/* Modal abonos */}
      {servicioAbono && (
        <ModalAbonos
          servicio={servicioAbono}
          onClose={() => setServicioAbono(null)}
          onAbonoRegistrado={fetchData}
        />
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package size={20} /> Servicios de Mano de Obra
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            {items.length} servicios registrados
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => navigate('/home')}
            style={{ ...styles.button, ...styles.cancelButton }}
          >
            Cancelar
          </button>

          <button
            onClick={() => navigate('/register-labour')}
            onMouseEnter={() => handleButtonHover('addNew', true)}
            onMouseLeave={() => handleButtonHover('addNew', false)}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '9px 18px', borderRadius: '10px', border: 'none',
              background: '#1d4ed8', color: '#fff', fontWeight: 500,
              fontSize: '14px', cursor: 'pointer'
            }}
          >
            <Plus size={16} /> Nuevo servicio
          </button>
        </div>
      </div>

      {/* Tarjetas métricas */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '12px', marginBottom: '24px' }}>
        {[
          { label: 'Total facturado', value: `$${metricas.total.toFixed(2)}`, icon: Package, color: '#374151' },
          { label: 'Total cobrado', value: `$${metricas.cobrado.toFixed(2)}`, icon: CheckCircle, color: '#15803d' },
          { label: 'Por cobrar', value: `$${metricas.pendiente.toFixed(2)}`, icon: AlertCircle, color: '#dc2626' },
          { label: 'En crédito', value: `${metricas.credito} servicios`, icon: CreditCard, color: '#1d4ed8' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} style={{
            background: 'var(--color-background-secondary, #f9fafb)',
            borderRadius: '12px', padding: '14px 16px',
            border: '0.5px solid var(--color-border-tertiary)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{label}</span>
              <Icon size={15} style={{ color }} />
            </div>
            <div style={{ fontSize: '18px', fontWeight: 500, color, marginTop: '6px' }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Búsqueda y filtros */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <input
            type="text"
            placeholder="Buscar por nombre, descripción o factura..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setPagination(p => ({ ...p, currentPage: 1 })); }}
            style={{ ...stylesAlmacens.searchInput, paddingLeft: '36px', width: '100%' }}
          />
          <div style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-secondary)' }}>
            <Search size={15} />
          </div>
        </div>
        {['todos', 'pendiente', 'parcial', 'pagado'].map(estado => (
          <button
            key={estado}
            onClick={() => { setFiltroEstado(estado); setPagination(p => ({ ...p, currentPage: 1 })); }}
            style={{
              padding: '8px 16px', borderRadius: '999px', fontSize: '13px', fontWeight: 500,
              cursor: 'pointer', border: '1px solid',
              background: filtroEstado === estado ? '#1d4ed8' : 'transparent',
              color: filtroEstado === estado ? '#fff' : 'var(--color-text-secondary)',
              borderColor: filtroEstado === estado ? '#1d4ed8' : 'var(--color-border-tertiary)'
            }}
          >
            {{ todos: 'Todos', pendiente: 'Pendientes', parcial: 'Parciales', pagado: 'Pagados' }[estado]}
          </button>
        ))}
      </div>

      {/* Tabla */}
      {loading ? (
        <div style={stylesAlmacens.loadingContainer}>
          <div style={stylesAlmacens.spinner}></div>
          <p>Cargando servicios...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div style={stylesAlmacens.emptyState}>
          <FileX size={48} />
          <h3>No se encontraron servicios</h3>
          <p>Intenta cambiar los filtros o añade un nuevo servicio.</p>
        </div>
      ) : (
        <>
          <div style={{ ...stylesAlmacens.tableContainer, borderRadius: '12px', border: '0.5px solid var(--color-border-tertiary)', overflow: 'hidden' }}>
            <table style={{ ...stylesAlmacens.table, borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr style={{ background: 'var(--color-background-secondary, #f9fafb)' }}>
                  <th style={thStyle('nombre_persona')} onClick={() => handleSort('nombre_persona')}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>Nombre {renderSortIcon('nombre_persona')}</span>
                  </th>
                  <th style={stylesAlmacens.tableHeader}>Descripción</th>
                  <th style={thStyle('precio_total')} onClick={() => handleSort('precio_total')}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>Precio {renderSortIcon('precio_total')}</span>
                  </th>
                  <th style={stylesAlmacens.tableHeader}>Abonado</th>
                  <th style={stylesAlmacens.tableHeader}>Pendiente</th>
                  <th style={stylesAlmacens.tableHeader}>Modalidad</th>
                  <th style={stylesAlmacens.tableHeader}>Estado</th>
                  <th style={stylesAlmacens.tableHeader}>Factura</th>
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
                      borderBottom: '0.5px solid var(--color-border-tertiary)'
                    }}
                    onMouseEnter={() => setHoveredRow(item.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <td style={{ ...stylesAlmacens.tableCell, fontWeight: 500 }}>
                      {item.nombre_persona}
                    </td>
                    <td style={{ ...stylesAlmacens.tableCell, maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                      {item.descripcion || '—'}
                    </td>
                    <td style={{ ...stylesAlmacens.tableCell, fontWeight: 500 }}>
                      ${parseFloat(item.precio_total).toFixed(2)}
                    </td>
                    <td style={{ ...stylesAlmacens.tableCell, color: '#15803d', fontWeight: 500 }}>
                      ${parseFloat(item.total_abonado || 0).toFixed(2)}
                    </td>
                    <td style={{ ...stylesAlmacens.tableCell, color: parseFloat(item.saldo_pendiente) > 0 ? '#dc2626' : '#15803d', fontWeight: 500 }}>
                      ${parseFloat(item.saldo_pendiente || 0).toFixed(2)}
                    </td>
                    <td style={stylesAlmacens.tableCell}>
                      <BadgeModalidad modalidad={item.modalidad_pago} />
                    </td>
                    <td style={stylesAlmacens.tableCell}>
                      <BadgeEstado estado={item.estado_pago} />
                    </td>
                    <td style={{ ...stylesAlmacens.tableCell, fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                      {item.factura_asociada || '—'}
                    </td>
                    <td style={stylesAlmacens.tableCell}>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        {/* Abono (solo crédito no pagado) */}
                        {item.modalidad_pago === 'credito' && item.estado_pago !== 'pagado' && (
                          <button
                            onClick={() => setServicioAbono(item)}
                            onMouseEnter={() => handleButtonHover(`abono-${item.id}`, true)}
                            onMouseLeave={() => handleButtonHover(`abono-${item.id}`, false)}
                            title="Registrar abono"
                            style={{
                              display: 'flex', alignItems: 'center', gap: '4px',
                              padding: '5px 10px', borderRadius: '8px', fontSize: '12px',
                              border: '1px solid #bfdbfe', background: buttonHoverStates[`abono-${item.id}`] ? '#dbeafe' : '#eff6ff',
                              color: '#1d4ed8', cursor: 'pointer', fontWeight: 500, whiteSpace: 'nowrap'
                            }}
                          >
                            <Wallet size={13} /> Abonar
                          </button>
                        )}
                        <button className="sl-act-btn sl-act-edit"
                          onClick={() => navigate(`/register-labour/${item.id}`)}
                          onMouseEnter={() => handleButtonHover(`edit-${item.id}`, true)}
                          onMouseLeave={() => handleButtonHover(`edit-${item.id}`, false)}
                          title="Editar"
                        >
                           <IconEdit />
                        </button>
                        
                        <button  className="sl-act-btn sl-act-del"
                          onClick={() => handleDelete(item.id)}
                          onMouseEnter={() => handleButtonHover(`del-${item.id}`, true)}
                          onMouseLeave={() => handleButtonHover(`del-${item.id}`, false)}
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

          {/* Paginación */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap', gap: '10px' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              Mostrando {paginatedItems.length} de {filteredItems.length} servicios
            </span>
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
              {[
                { icon: ChevronsLeft, action: () => setPagination(p => ({ ...p, currentPage: 1 })), disabled: pagination.currentPage === 1 },
                { icon: ChevronLeft, action: () => setPagination(p => ({ ...p, currentPage: p.currentPage - 1 })), disabled: pagination.currentPage === 1 },
                { icon: ChevronRight, action: () => setPagination(p => ({ ...p, currentPage: p.currentPage + 1 })), disabled: pagination.currentPage === totalPages },
                { icon: ChevronsRight, action: () => setPagination(p => ({ ...p, currentPage: totalPages })), disabled: pagination.currentPage === totalPages },
              ].map(({ icon: Icon, action, disabled }, i) => (
                <button key={i} onClick={action} disabled={disabled} style={{
                  ...stylesAlmacens.paginationButton,
                  ...(disabled ? stylesAlmacens.paginationButtonDisabled : {})
                }}>
                  <Icon size={15} />
                </button>
              ))}
              <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)', padding: '0 8px' }}>
                {pagination.currentPage} / {totalPages}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default LabourList;