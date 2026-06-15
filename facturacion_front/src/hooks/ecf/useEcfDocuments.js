import { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { ecfApi } from '../../services/ecf/ecfApi';
import { usePolling } from './usePolling';

const initialFilters = {
  search: '',
  status: undefined,
  fiscal_status: undefined,
  job_status: undefined,
  ecf_type: undefined,
  ordering: '-created_at',
};

export function useEcfDocuments({ poll = true } = {}) {
  const [documents, setDocuments] = useState([]);
  const [monitor, setMonitor] = useState(null);
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
      status: filters.status || undefined,
      fiscal_status: filters.fiscal_status || undefined,
      job_status: filters.job_status || undefined,
      ecf_type: filters.ecf_type || undefined,
      ordering: filters.ordering || undefined,
    };
    Object.keys(clean).forEach((key) => clean[key] === undefined && delete clean[key]);
    return clean;
  }, [filters, page, pageSize]);

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    setError(null);
    try {
      const [documentsResponse, monitorResponse] = await Promise.all([
        ecfApi.listDocuments(params),
        ecfApi.getMonitor(),
      ]);
      setDocuments(documentsResponse.results);
      setTotal(documentsResponse.count);
      setMonitor(monitorResponse);
    } catch (err) {
      const detail = err.response?.data?.detail || 'No se pudo cargar el panel e-CF.';
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

  const runAction = useCallback(async (key, action) => {
    setActionLoading((current) => ({ ...current, [key]: true }));
    try {
      const result = await action();
      message.success(result?.enqueued === false ? 'No fue necesario encolar la operación.' : 'Operación encolada.');
      await refresh({ quiet: true });
      return result;
    } catch (err) {
      const detail = err.response?.data?.detail || 'No se pudo ejecutar la acción.';
      message.error(detail);
      throw err;
    } finally {
      setActionLoading((current) => ({ ...current, [key]: false }));
    }
  }, [refresh]);

  const actions = {
    process: (id) => runAction(`process-${id}`, () => ecfApi.processDocument(id)),
    retry: (id) => runAction(`retry-${id}`, () => ecfApi.retrySubmission(id)),
    checkStatus: (id) => runAction(`status-${id}`, () => ecfApi.checkStatus(id)),
    submit: (id) => runAction(`submit-${id}`, () => ecfApi.submitDocument(id)),
  };

  return {
    documents,
    monitor,
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
