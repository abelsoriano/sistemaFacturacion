import { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import api from '../../services/api';
import { usePolling } from './usePolling';

const normalizeList = (data) => {
  if (Array.isArray(data)) {
    return { results: data, count: data.length };
  }
  return {
    results: data?.results || [],
    count: data?.count || data?.results?.length || 0,
  };
};

const initialFilters = {
  search: '',
  ecf_fiscal_status: undefined,
  ecf_job_status: undefined,
  fiscal_resolution_status: undefined,
  inventory_reconciliation_status: undefined,
  requires_manual_review: undefined,
  client: undefined,
  created_at_from: undefined,
  created_at_to: undefined,
};

export function useE34CreditNotes({ poll = true } = {}) {
  const [notes, setNotes] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState(initialFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [error, setError] = useState(null);

  const params = useMemo(() => {
    const clean = {
      page,
      page_size: pageSize,
      search: filters.search || undefined,
      ecf_fiscal_status: filters.ecf_fiscal_status || undefined,
      ecf_job_status: filters.ecf_job_status || undefined,
      fiscal_resolution_status: filters.fiscal_resolution_status || undefined,
      inventory_reconciliation_status: filters.inventory_reconciliation_status || undefined,
      requires_manual_review: filters.requires_manual_review,
      client: filters.client || undefined,
      created_at_from: filters.created_at_from || undefined,
      created_at_to: filters.created_at_to || undefined,
    };
    Object.keys(clean).forEach((key) => (clean[key] === undefined || clean[key] === '') && delete clean[key]);
    return clean;
  }, [filters, page, pageSize]);

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    setError(null);
    try {
      const [notesResponse, summaryResponse] = await Promise.all([
        api.get('/credit-notes/', { params }),
        api.get('/credit-notes/fiscal-summary/', { params }),
      ]);
      const normalized = normalizeList(notesResponse.data);
      setNotes(normalized.results);
      setTotal(normalized.count);
      setSummary(summaryResponse.data);
    } catch (err) {
      const detail = err.response?.data?.detail || 'No se pudieron cargar las notas E34.';
      setError(detail);
      if (!quiet) message.error(detail);
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  usePolling(() => refresh({ quiet: true }), 15000, poll);

  const runAction = useCallback(async (key, successMessage, action) => {
    setActionLoading((current) => ({ ...current, [key]: true }));
    try {
      const result = await action();
      message.success(result?.data?.message || successMessage);
      await refresh({ quiet: true });
      return result?.data;
    } catch (err) {
      const detail = err.response?.data?.detail || 'No se pudo ejecutar la acción E34.';
      message.error(detail);
      throw err;
    } finally {
      setActionLoading((current) => ({ ...current, [key]: false }));
    }
  }, [refresh]);

  const actions = {
    checkStatus: (id) => runAction(`status-${id}`, 'Consulta DGII encolada.', () => api.post(`/credit-notes/${id}/check-status/`)),
    retry: (id) => runAction(`retry-${id}`, 'Retry E34 encolado.', () => api.post(`/credit-notes/${id}/retry/`)),
    reconcileInventory: (id) => runAction(`reconcile-${id}`, 'Inventario compensado.', () => api.post(`/credit-notes/${id}/reconcile-inventory/`)),
    markReviewed: (id) => runAction(`review-${id}`, 'Revisión registrada.', () => api.post(`/credit-notes/${id}/mark-reviewed/`)),
  };

  return {
    notes,
    summary,
    filters,
    setFilters,
    page,
    setPage,
    pageSize,
    setPageSize,
    total,
    loading,
    actionLoading,
    error,
    refresh,
    actions,
  };
}
