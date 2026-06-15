import api from './api';

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

export const quotationService = {
  async list(params = {}) {
    const response = await api.get('/quotations/', { params });
    return normalizeList(response.data);
  },

  async get(id) {
    const response = await api.get(`/quotations/${id}/`);
    return response.data;
  },

  async create(payload) {
    const response = await api.post('/quotations/', payload);
    return response.data;
  },

  async update(id, payload) {
    const response = await api.put(`/quotations/${id}/`, payload);
    return response.data;
  },

  async send(id) {
    const response = await api.post(`/quotations/${id}/send/`);
    return response.data;
  },

  async approve(id) {
    const response = await api.post(`/quotations/${id}/approve/`);
    return response.data;
  },

  async reject(id) {
    const response = await api.post(`/quotations/${id}/reject/`);
    return response.data;
  },

  async expire(id) {
    const response = await api.post(`/quotations/${id}/expire/`);
    return response.data;
  },

  async convertToInvoice(id, payload = {}) {
    const response = await api.post(`/quotations/${id}/convert-to-invoice/`, payload);
    return response.data;
  },
};
