import api from '../api';

const normalizeList = (data) => {
  if (Array.isArray(data)) {
    return { results: data, count: data.length };
  }
  return {
    results: data?.results || [],
    count: data?.count || data?.results?.length || 0,
    next: data?.next || null,
    previous: data?.previous || null,
  };
};

export const ecfApi = {
  async listDocuments(params = {}) {
    const response = await api.get('/ecf/documents/', { params });
    return normalizeList(response.data);
  },

  async getDocument(id) {
    const response = await api.get(`/ecf/documents/${id}/`);
    return response.data;
  },

  async getMonitor() {
    const response = await api.get('/ecf/documents/async-monitor/');
    return response.data;
  },

  async processDocument(id, payload = {}) {
    const response = await api.post(`/ecf/documents/${id}/process-async/`, payload);
    return response.data;
  },

  async retrySubmission(id, payload = {}) {
    const response = await api.post(`/ecf/documents/${id}/retry-submission-async/`, payload);
    return response.data;
  },

  async checkStatus(id, payload = {}) {
    const response = await api.post(`/ecf/documents/${id}/check-dgii-status-async/`, payload);
    return response.data;
  },

  async submitDocument(id, payload = {}) {
    const response = await api.post(`/ecf/documents/${id}/submit-dgii-async/`, payload);
    return response.data;
  },

  artifactUrl(id, artifact) {
    const baseUrl = api.defaults.baseURL || '';
    return `${baseUrl}/ecf/documents/${id}/audit-artifact/${artifact}/`;
  },
};

export const downloadXml = (filename, content) => {
  const blob = new Blob([content || ''], { type: 'application/xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const downloadFiscalArtifact = async (documentId, artifact, filename) => {
  const response = await api.get(`/ecf/documents/${documentId}/audit-artifact/${artifact}/`, {
    responseType: 'blob',
  });
  const blob = new Blob([response.data], { type: 'application/xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
