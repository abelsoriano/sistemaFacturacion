import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import { FaArrowLeft, FaCalendarAlt, FaFileAlt, FaPlus, FaSave, FaTrash, FaUser } from 'react-icons/fa';
import api from '../services/api';
import { quotationService } from '../services/quotations';
import '../css/quotationList.css';

const money = (value) => `$${Number(value || 0).toFixed(2)}`;
const moneyNumber = (value) => Number((Number(value) || 0).toFixed(2));

function QuotationForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState({
    client: '',
    customer_name: '',
    valid_until: '',
    notes: '',
    discount: 0,
    apply_itbis: true,
    details: [],
  });

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [clientsRes, productsRes] = await Promise.all([
          api.get('/clients/'),
          api.get('/products/'),
        ]);
        setClients(Array.isArray(clientsRes.data) ? clientsRes.data : clientsRes.data.results || []);
        setProducts(Array.isArray(productsRes.data) ? productsRes.data : productsRes.data.results || []);
        if (id) {
          const quote = await quotationService.get(id);
          setDraft({
            client: quote.client || '',
            customer_name: quote.customer_name || '',
            valid_until: quote.valid_until || '',
            notes: quote.notes || '',
            discount: Number(quote.discount || 0),
            apply_itbis: Number(quote.tax || 0) > 0,
            details: (quote.details || []).map((detail) => ({
              product: detail.product,
              product_name: detail.product_name,
              quantity: detail.quantity,
              price: Number(detail.price),
              subtotal: Number(detail.subtotal),
            })),
          });
        }
      } catch (error) {
        toast.error('No se pudo cargar el formulario');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const subtotal = useMemo(
    () => moneyNumber(draft.details.reduce((total, item) => total + Number(item.quantity || 0) * Number(item.price || 0), 0)),
    [draft.details],
  );
  const discount = moneyNumber(Math.min(Number(draft.discount || 0), subtotal));
  const tax = moneyNumber(draft.apply_itbis ? (subtotal - discount) * 0.18 : 0);
  const total = moneyNumber(subtotal - discount + tax);

  const addProduct = (productId) => {
    const product = products.find((item) => String(item.id) === String(productId));
    if (!product) return;
    if (draft.details.some((item) => String(item.product) === String(product.id))) {
      toast.error('El producto ya está en la cotización');
      return;
    }
    setDraft((current) => ({
      ...current,
      details: [
        ...current.details,
        {
          product: product.id,
          product_name: product.name,
          quantity: 1,
          price: Number(product.price),
          subtotal: Number(product.price),
        },
      ],
    }));
  };

  const updateDetail = (index, field, value) => {
    setDraft((current) => {
      const details = [...current.details];
      const next = { ...details[index], [field]: field === 'quantity' ? Math.max(1, parseInt(value, 10) || 1) : Number(value || 0) };
      next.subtotal = next.quantity * next.price;
      details[index] = next;
      return { ...current, details };
    });
  };

  const removeDetail = (index) => {
    setDraft((current) => ({ ...current, details: current.details.filter((_, itemIndex) => itemIndex !== index) }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!draft.client && !draft.customer_name.trim()) {
      toast.error('Selecciona un cliente o escribe un nombre de cliente');
      return;
    }
    if (!draft.details.length) {
      toast.error('Agrega al menos un producto');
      return;
    }
    setLoading(true);
    const payload = {
      customer_name: draft.customer_name || null,
      valid_until: draft.valid_until || null,
      notes: draft.notes,
      discount: moneyNumber(discount),
      apply_itbis: draft.apply_itbis,
      details: draft.details.map((item) => ({
        product: item.product,
        quantity: item.quantity,
        price: moneyNumber(item.price),
      })),
    };
    if (draft.client) {
      payload.client_id = draft.client;
    }
    try {
      if (id) {
        await quotationService.update(id, payload);
        toast.success('Cotización actualizada');
      } else {
        await quotationService.create(payload);
        toast.success('Cotización creada');
      }
      navigate('/quotations');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo guardar la cotización');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="qtn-page">
      <Toaster position="top-right" />
      <header className="qtn-header">
        <div>
          <span className="qtn-eyebrow">Cotización</span>
          <h1>{id ? 'Editar cotización' : 'Nueva cotización'}</h1>
          <p>Documento comercial no fiscal. Los productos se reservan visualmente, sin afectar stock real.</p>
        </div>
        <div className="qtn-header-actions">
          <button className="qtn-btn secondary" onClick={() => navigate('/quotations')} type="button">
            <FaArrowLeft /> Volver
          </button>
          <button className="qtn-btn primary" onClick={submit} disabled={loading} type="button">
            <FaSave /> {loading ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </header>

      <form className="qtn-form-layout" onSubmit={submit}>
        <main className="qtn-form-main">
          <section className="qtn-panel">
            <div className="qtn-panel-head">
              <div>
                <span>Productos</span>
                <h2>Detalle de la cotización</h2>
              </div>
              <label className="qtn-product-picker">
                <FaPlus />
                <select onChange={(event) => { addProduct(event.target.value); event.target.value = ''; }} defaultValue="">
                  <option value="">Agregar producto...</option>
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>{product.name} - {money(product.price)}</option>
                  ))}
                </select>
              </label>
            </div>

            {draft.details.length === 0 ? (
              <div className="qtn-empty-state compact">Agrega productos para cotizar.</div>
            ) : (
              <div className="qtn-form-table-wrap">
                <table className="qtn-form-table">
                  <thead>
                    <tr>
                      <th>Producto</th>
                      <th>Cant.</th>
                      <th>Precio</th>
                      <th>Subtotal</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {draft.details.map((item, index) => (
                      <tr key={`${item.product}-${index}`}>
                        <td data-label="Producto">
                          <strong>{item.product_name}</strong>
                        </td>
                        <td data-label="Cant.">
                          <input className="qtn-small-input" type="number" min="1" value={item.quantity} onChange={(event) => updateDetail(index, 'quantity', event.target.value)} />
                        </td>
                        <td data-label="Precio">
                          <input className="qtn-price-input" type="number" step="0.01" value={item.price} onChange={(event) => updateDetail(index, 'price', event.target.value)} />
                        </td>
                        <td data-label="Subtotal" className="qtn-money">{money(item.subtotal)}</td>
                        <td data-label="Acción">
                          <button type="button" className="qtn-icon-btn danger" onClick={() => removeDetail(index)}>
                            <FaTrash /> Quitar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="qtn-panel">
            <div className="qtn-panel-head">
              <div>
                <span>Notas</span>
                <h2>Condiciones comerciales</h2>
              </div>
              <FaFileAlt />
            </div>
            <div className="qtn-panel-body">
              <textarea
                rows="5"
                value={draft.notes}
                onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
                placeholder="Notas comerciales, condiciones o comentarios para el cliente..."
              />
            </div>
          </section>
        </main>

        <aside className="qtn-form-side">
          <section className="qtn-panel">
            <div className="qtn-panel-head">
              <div>
                <span>Cliente</span>
                <h2>Datos del receptor</h2>
              </div>
              <FaUser />
            </div>
            <div className="qtn-panel-body">
              <label className="qtn-field">
                <span>Cliente registrado</span>
                <select value={draft.client} onChange={(event) => setDraft({ ...draft, client: event.target.value })}>
                  <option value="">Cliente no registrado</option>
                  {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
                </select>
              </label>

              {!draft.client && (
                <label className="qtn-field">
                  <span>Nombre libre</span>
                  <input value={draft.customer_name} onChange={(event) => setDraft({ ...draft, customer_name: event.target.value })} placeholder="Nombre del cliente" />
                </label>
              )}

              <label className="qtn-field">
                <span>Validez</span>
                <div className="qtn-input-icon">
                  <FaCalendarAlt />
                  <input type="date" value={draft.valid_until} onChange={(event) => setDraft({ ...draft, valid_until: event.target.value })} />
                </div>
              </label>
            </div>
          </section>

          <section className="qtn-panel">
            <div className="qtn-panel-head">
              <div>
                <span>Totales</span>
                <h2>Resumen comercial</h2>
              </div>
            </div>
            <div className="qtn-panel-body">
              <label className="qtn-field">
                <span>Descuento</span>
                <input type="number" step="0.01" value={draft.discount} onChange={(event) => setDraft({ ...draft, discount: Number(event.target.value || 0) })} placeholder="Descuento" />
              </label>
              <div className="qtn-total-lines">
                <div><span>Subtotal</span><strong>{money(subtotal)}</strong></div>
                <div><span>Descuento</span><strong>{money(discount)}</strong></div>
                <div><span>ITBIS {draft.apply_itbis ? '18%' : '0%'}</span><strong>{money(tax)}</strong></div>
                <div className="grand-total"><span>Total</span><strong>{money(total)}</strong></div>
              </div>
              <label className="qtn-tax-toggle">
                <input
                  type="checkbox"
                  checked={draft.apply_itbis}
                  onChange={(event) => setDraft({ ...draft, apply_itbis: event.target.checked })}
                />
                <span>Aplicar ITBIS</span>
              </label>
            </div>
          </section>
        </aside>
      </form>
    </div>
  );
}

export default QuotationForm;
