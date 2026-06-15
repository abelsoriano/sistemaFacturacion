import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import Swal from 'sweetalert2';
import { FaCheck, FaEdit, FaExchangeAlt, FaPaperPlane, FaPlus, FaSearch, FaTimes } from 'react-icons/fa';
import { quotationService } from '../services/quotations';
import '../css/quotationList.css';

const STATUS = {
  draft: { label: 'Borrador', cls: 'draft' },
  sent: { label: 'Enviada', cls: 'sent' },
  approved: { label: 'Aprobada', cls: 'approved' },
  rejected: { label: 'Rechazada', cls: 'rejected' },
  expired: { label: 'Expirada', cls: 'expired' },
};

const money = (value) => `$${Number(value || 0).toFixed(2)}`;

function QuotationList() {
  const navigate = useNavigate();
  const [quotations, setQuotations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');

  const load = async () => {
    setLoading(true);
    try {
      setQuotations(await quotationService.list());
    } catch (error) {
      toast.error('No se pudieron cargar las cotizaciones');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const text = query.toLowerCase();
    return quotations.filter((item) => {
      const matchStatus = status === 'all' || item.status === status;
      const matchText = !text
        || item.quotation_number?.toLowerCase().includes(text)
        || item.customer_display?.toLowerCase().includes(text)
        || item.client_name?.toLowerCase().includes(text);
      return matchStatus && matchText;
    });
  }, [quotations, query, status]);

  const stats = useMemo(() => {
    const draftCount = quotations.filter((item) => ['draft', 'sent'].includes(item.status)).length;
    const convertedCount = quotations.filter((item) => item.invoice_id || item.invoice_number).length;
    const approvedCount = quotations.filter((item) => item.status === 'approved').length;
    const totalAmount = quotations.reduce((sum, item) => sum + Number(item.total || 0), 0);
    return {
      total: quotations.length,
      draftCount,
      convertedCount,
      approvedCount,
      totalAmount,
    };
  }, [quotations]);

  const transition = async (id, action) => {
    try {
      await quotationService[action](id);
      toast.success('Cotización actualizada');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo actualizar la cotización');
    }
  };

  const convert = async (id) => {
    try {
      const resultConfirm = await Swal.fire({
        title: 'Convertir a factura pendiente',
        text: 'Se creará una factura pendiente de cobro. Podrás cobrarla y emitirla luego desde la factura.',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#6C63FF',
        confirmButtonText: 'Continuar',
        cancelButtonText: 'Cancelar',
      });
      if (!resultConfirm.isConfirmed) return;
      const result = await quotationService.convertToInvoice(id, { status: 'pending', payment_method: 'cash' });
      toast.success(`Factura pendiente creada: ${result.invoice_number}`);
      navigate(`/invoices/${result.invoice_id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo convertir la cotización');
    }
  };

  return (
    <div className="qtn-page">
      <Toaster position="top-right" />
      <header className="qtn-header">
        <div>
          <span className="qtn-eyebrow">Comercial</span>
          <h1>Cotizaciones</h1>
          <p>Documento comercial no fiscal. Al convertir, crea una factura pendiente; el stock y e-CF se procesan al cobrar y emitir.</p>
        </div>
        <button className="qtn-btn primary" onClick={() => navigate('/quotations/new')}>
          <FaPlus /> Nueva cotización
        </button>
      </header>

      <section className="qtn-stats-grid" aria-label="Resumen de cotizaciones">
        <div className="qtn-stat-card">
          <span>Total cotizaciones</span>
          <strong>{stats.total}</strong>
          <small>Registros comerciales</small>
        </div>
        <div className="qtn-stat-card">
          <span>Borradores / enviadas</span>
          <strong>{stats.draftCount}</strong>
          <small>Pendientes de decisión</small>
        </div>
        <div className="qtn-stat-card">
          <span>Convertidas</span>
          <strong>{stats.convertedCount}</strong>
          <small>Con factura creada</small>
        </div>
        <div className="qtn-stat-card">
          <span>Monto total</span>
          <strong>{money(stats.totalAmount)}</strong>
          <small>{stats.approvedCount} aprobadas</small>
        </div>
      </section>

      <section className="qtn-filter-card">
        <div className="qtn-filter-title">
          <FaSearch /> Filtros
        </div>
        <div className="qtn-filter-grid">
          <label>
            <span>Buscar</span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Número o cliente"
            />
          </label>
          <label>
            <span>Estado</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="all">Todos los estados</option>
              {Object.entries(STATUS).map(([key, config]) => (
                <option key={key} value={key}>{config.label}</option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="qtn-table-card">
        <div className="qtn-table-head">
          <div>
            <strong>Listado</strong>
            <span>{filtered.length} resultado(s)</span>
          </div>
        </div>

        {loading ? (
          <div className="qtn-empty-state">Cargando cotizaciones...</div>
        ) : filtered.length === 0 ? (
          <div className="qtn-empty-state">No hay cotizaciones para mostrar.</div>
        ) : (
          <table className="qtn-table">
            <thead>
              <tr>
                <th>Número</th>
                <th>Cliente</th>
                <th>Estado</th>
                <th>Total</th>
                <th>Validez</th>
                <th>Factura</th>
                <th className="qtn-actions-col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((quote) => {
                const config = STATUS[quote.status] || STATUS.draft;
                const canConvert = quote.status === 'approved' && !quote.invoice_id;
                return (
                  <tr key={quote.id}>
                    <td data-label="Número"><strong className="qtn-number">{quote.quotation_number}</strong></td>
                    <td data-label="Cliente">{quote.customer_display || quote.client_name || '—'}</td>
                    <td data-label="Estado">
                      <span className={`qtn-status ${config.cls}`}>{config.label}</span>
                    </td>
                    <td data-label="Total" className="qtn-money">{money(quote.total)}</td>
                    <td data-label="Validez">{quote.valid_until || 'Sin vencimiento'}</td>
                    <td data-label="Factura">
                      {quote.invoice_number ? <span className="qtn-invoice-link">{quote.invoice_number}</span> : <span className="qtn-muted">—</span>}
                    </td>
                    <td data-label="Acciones">
                      <div className="qtn-row-actions">
                        <button className="qtn-icon-btn" onClick={() => navigate(`/quotations/${quote.id}/edit`)}>
                          <FaEdit /> Editar
                        </button>
                        {quote.status === 'draft' && (
                          <button className="qtn-icon-btn" onClick={() => transition(quote.id, 'send')}>
                            <FaPaperPlane /> Enviar
                          </button>
                        )}
                        {['draft', 'sent'].includes(quote.status) && (
                          <>
                            <button className="qtn-icon-btn success" onClick={() => transition(quote.id, 'approve')}>
                              <FaCheck /> Aprobar
                            </button>
                            <button className="qtn-icon-btn danger" onClick={() => transition(quote.id, 'reject')}>
                              <FaTimes /> Rechazar
                            </button>
                          </>
                        )}
                        {canConvert && (
                          <button className="qtn-icon-btn primary" onClick={() => convert(quote.id)}>
                            <FaExchangeAlt /> Convertir a factura pendiente
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default QuotationList;
