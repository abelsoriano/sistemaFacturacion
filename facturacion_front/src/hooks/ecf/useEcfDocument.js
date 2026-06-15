import { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';
import { ecfApi } from '../../services/ecf/ecfApi';
import { usePolling } from './usePolling';

export function useEcfDocument(id, { poll = true } = {}) {
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!id) return;
    if (!quiet) setLoading(true);
    try {
      const response = await ecfApi.getDocument(id);
      setDocument(response);
    } catch (err) {
      const detail = err.response?.data?.detail || 'No se pudo cargar el documento e-CF.';
      if (!quiet) message.error(detail);
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  usePolling(() => refresh({ quiet: true }), 15000, poll && Boolean(id));

  const runAction = useCallback(async (key, action) => {
    setActionLoading((current) => ({ ...current, [key]: true }));
    try {
      const result = await action();
      message.success(result?.enqueued === false ? 'Sin cambios pendientes.' : 'Operación encolada.');
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

  return {
    document,
    loading,
    actionLoading,
    refresh,
    actions: {
      process: () => runAction('process', () => ecfApi.processDocument(id)),
      retry: () => runAction('retry', () => ecfApi.retrySubmission(id)),
      checkStatus: () => runAction('status', () => ecfApi.checkStatus(id)),
      submit: () => runAction('submit', () => ecfApi.submitDocument(id)),
    },
  };
}
