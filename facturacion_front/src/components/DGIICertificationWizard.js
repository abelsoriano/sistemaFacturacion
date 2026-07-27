import React, { useEffect, useMemo, useState } from 'react';
import Swal from 'sweetalert2';
import {
  AlertTriangle,
  Download,
  ExternalLink,
  FileCheck2,
  FileSignature,
  FileUp,
  Info,
  Search,
  ShieldCheck,
} from 'lucide-react';

import api from '../services/api';
import notify from '../utils/notify';
import '../css/DGIICertificationWizard.css';

const MAX_XML_BYTES = 2 * 1024 * 1024;
const STORAGE_KEY = 'dgii_certification_wizard_state';
const MAX_EXCEL_BYTES = 5 * 1024 * 1024;
const PAGE_SIZE = 8;

const normalizeList = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

const applicationStates = [
  { value: 'not_started', label: 'No iniciada' },
  { value: 'xml_generated', label: 'XML generado' },
  { value: 'xml_signed', label: 'XML firmado' },
  { value: 'sent_to_dgii', label: 'Enviada a DGII' },
  { value: 'approved', label: 'Aprobada' },
];

const certificationFlowSteps = [
  { id: 1, title: 'Registrado' },
  { id: 2, title: 'Pruebas de Datos e-CF' },
  { id: 3, title: 'Pruebas de Datos Aprobación Comercial' },
  { id: 4, title: 'Pruebas Simulación e-CF' },
  { id: 5, title: 'Pruebas Simulación Representación Impresa' },
  { id: 6, title: 'Validación Representación Impresa' },
  { id: 7, title: 'URL Servicios Prueba' },
  { id: 8, title: 'Inicio Prueba Recepción e-CF' },
  { id: 9, title: 'Recepción e-CF' },
  { id: 10, title: 'Inicio Prueba Recepción Aprobación Comercial' },
  { id: 11, title: 'Recepción Aprobación Comercial' },
  { id: 12, title: 'URL Servicios Producción' },
  { id: 13, title: 'Declaración Jurada' },
  { id: 14, title: 'Verificación Estatus' },
  { id: 15, title: 'Finalizado' },
];

function formatDate(value, withTime = false) {
  if (!value) return 'No disponible';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No disponible';
  return date.toLocaleString('es-DO', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  });
}

function compact(value, length = 28) {
  if (!value) return 'No disponible';
  if (value.length <= length) return value;
  return `${value.slice(0, Math.max(8, length - 12))}...${value.slice(-8)}`;
}

function loadLocalState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (_err) {
    return {};
  }
}

function saveLocalState(nextState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState));
}

function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: 'application/xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function confirmDgiiAction({ title, text, confirmButtonText }) {
  const result = await Swal.fire({
    title,
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText,
    cancelButtonText: 'Cancelar',
    reverseButtons: true,
  });
  return result.isConfirmed;
}

function getXmlInfo(file, content) {
  const parser = new DOMParser();
  const documentXml = parser.parseFromString(content, 'application/xml');
  if (documentXml.querySelector('parsererror')) {
    throw new Error('El archivo seleccionado no contiene XML válido.');
  }
  const root = documentXml.documentElement;
  return {
    filename: file.name,
    size: file.size,
    rootName: root?.nodeName || 'XML',
    uploadedAt: new Date().toISOString(),
  };
}

function statusBadge(meta, fallback = 'No disponible') {
  const info = meta || { label: fallback, tone: 'neutral' };
  return <span className={`dgii-wizard-badge ${info.tone}`}>{info.label}</span>;
}

function hasRetryableSignedXml(item) {
  const document = item?.certification_document;
  if (!document) return false;
  return ['signed', 'submit_error'].includes(document.status) && Boolean(document.signed_xml_available || document.signed_xml_hash || document.signed_at);
}

function hasSignedXml(item) {
  const document = item?.certification_document;
  if (!document) return false;
  return Boolean(document.signed_xml_available || document.signed_xml_hash || document.signed_at);
}

function certificationStatusMeta(item) {
  if (String(item?.dgii_group) === '4' && hasSignedXml(item)) {
    if (item?.certification_document?.status === 'accepted_by_portal') {
      return { label: 'Aceptada en portal', tone: 'success' };
    }
    if (item?.certification_document?.status === 'uploaded_to_portal') {
      return { label: 'Cargada en portal', tone: 'info' };
    }
    return { label: 'XML listo para portal', tone: 'info' };
  }
  if (item?.certification_document?.needs_resubmit || item?.certification_document?.accepted_stale) {
    return { label: 'Requiere reenvío', tone: 'warning' };
  }
  if (item?.certification_document?.status === 'submit_conflict') {
    return { label: 'Secuencia ya usada', tone: 'warning' };
  }
  if (item?.certification_document?.status === 'accepted') {
    return { label: item.status_label || 'Aceptado', tone: 'success' };
  }
  if (['rejected', 'submit_error', 'generation_error', 'signing_error'].includes(item?.certification_document?.status || item?.status)) {
    return { label: item.status_label || 'Error', tone: 'danger' };
  }
  return { label: item?.status_label || 'Pendiente', tone: 'neutral' };
}

function isAcceptedItem(item) {
  return item?.certification_document?.status === 'accepted'
    && !item?.certification_document?.needs_resubmit
    && !item?.certification_document?.accepted_stale;
}

function isPendingResendItem(item) {
  return Boolean(item?.certification_document?.needs_resubmit || item?.certification_document?.accepted_stale);
}

function isRejectedItem(item) {
  return ['rejected', 'submit_error', 'generation_error', 'signing_error'].includes(
    item?.certification_document?.status || item?.status,
  );
}

function dgiiShortMessage(item) {
  const document = item?.certification_document;
  const message = document?.dgii_response_message || document?.submit_error || item?.generation_error || '';
  if (!message) return 'Sin mensaje DGII.';
  return message;
}

function getGroupStats(items = []) {
  const total = items.length;
  const pendingResend = items.filter(isPendingResendItem).length;
  const accepted = pendingResend > 0 ? 0 : items.filter(isAcceptedItem).length;
  const rejected = items.filter((item) => item.certification_document?.status === 'rejected').length;
  const conflicts = items.filter((item) => item.certification_document?.status === 'submit_conflict').length;
  const submitted = items.filter((item) => item.certification_document?.status === 'submitted').length;
  const signed = items.filter((item) => item.certification_document?.status === 'signed' && !isPendingResendItem(item)).length;
  const retryable = items.filter((item) => item.certification_document?.status === 'submit_error' && hasRetryableSignedXml(item)).length;
  const ready = signed + retryable;
  const prepared = items.filter((item) => ['generated', 'signed', 'submitted', 'accepted', 'rejected', 'submit_error', 'submit_conflict'].includes(item.certification_document?.status)).length;
  const pending = Math.max(total - accepted - rejected - conflicts - submitted - ready, 0);
  return {
    total,
    accepted,
    pendingResend,
    rejected,
    conflicts,
    submitted,
    signed,
    retryable,
    ready,
    prepared,
    pending,
    progress: total ? Math.round((accepted / total) * 100) : 0,
    complete: total > 0 && accepted === total && pendingResend === 0,
    canPrepare: total > 0 && (pendingResend > 0 || (ready < total && accepted + conflicts < total)),
    canSubmit: total > 0 && pendingResend === 0 && ready === total,
  };
}

function statsWithFallback(items = [], fallbackTotal = 0) {
  const stats = getGroupStats(items);
  const total = stats.total || fallbackTotal || 0;
  const pending = stats.total ? stats.pending : total;
  const ready = stats.ready || 0;
  const accepted = (stats.pendingResend || 0) > 0 ? 0 : (stats.accepted || 0);
  const conflicts = stats.conflicts || 0;
  return {
    ...stats,
    total,
    pending,
    progress: total ? Math.round((accepted / total) * 100) : 0,
    accepted,
    complete: total > 0 && accepted === total && (stats.pendingResend || 0) === 0,
    canPrepare: total > 0 && ((stats.pendingResend || 0) > 0 || (ready < total && accepted + conflicts < total)),
    canSubmit: total > 0 && (stats.pendingResend || 0) === 0 && ready === total,
  };
}

export default function DGIICertificationWizard() {
  const [company, setCompany] = useState(null);
  const [issuers, setIssuers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [commercialApprovalPlan, setCommercialApprovalPlan] = useState(null);
  const [selectedIssuerId, setSelectedIssuerId] = useState('');
  const [loading, setLoading] = useState(true);
  const [signing, setSigning] = useState(false);
  const [importingSet, setImportingSet] = useState(false);
  const [importingCommercialApprovals, setImportingCommercialApprovals] = useState(false);
  const [generatingXml, setGeneratingXml] = useState('');
  const [error, setError] = useState('');
  const [activeStep, setActiveStep] = useState(1);
  const [xmlFile, setXmlFile] = useState(null);
  const [xmlInfo, setXmlInfo] = useState(null);
  const [signedXml, setSignedXml] = useState('');
  const [signedFilename, setSignedFilename] = useState('postulacion-dgii-firmado.xml');
  const [applicationState, setApplicationState] = useState(() => loadLocalState().applicationState || 'not_started');

  const selectedIssuer = useMemo(
    () => issuers.find((issuer) => String(issuer.id) === String(selectedIssuerId)) || null,
    [issuers, selectedIssuerId],
  );
  const activeCertificate = selectedIssuer?.certificates?.find((certificate) => certificate.is_active) || null;
  const latestPlan = plans[0] || null;

  const updateApplicationState = (nextState) => {
    setApplicationState(nextState);
    saveLocalState({ ...loadLocalState(), applicationState: nextState });
  };

  const loadData = React.useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [companyResponse, issuersResponse] = await Promise.all([
        api.get('/companies/active/'),
        api.get('/ecf/issuers/'),
      ]);
      let plansResponse = await api.get('/ecf/certification-plans/').catch(() => ({ data: [] }));
      const commercialApprovalResponse = await api
        .get('/ecf/certification-commercial-approvals/latest/')
        .catch(() => ({ data: null }));
      const planList = normalizeList(plansResponse.data);
      if (planList[0]?.id) {
        const syncResponse = await api.post(`/ecf/certification-plans/${planList[0].id}/sync-reset-state/`).catch(() => null);
        if (syncResponse?.data?.summary?.total_marked) {
          plansResponse = await api.get('/ecf/certification-plans/').catch(() => plansResponse);
        }
      }
      const issuerList = normalizeList(issuersResponse.data);
      const issuersWithCertificates = await Promise.all(
        issuerList.map(async (issuer) => {
          try {
            const response = await api.get(`/ecf/issuers/${issuer.id}/certificates/`);
            return { ...issuer, certificates: normalizeList(response.data) };
          } catch (_err) {
            return { ...issuer, certificates: [] };
          }
        }),
      );

      setCompany(companyResponse.data?.active_company || null);
      setIssuers(issuersWithCertificates);
      setPlans(normalizeList(plansResponse.data));
      setCommercialApprovalPlan(commercialApprovalResponse.data || null);
      if (!selectedIssuerId && issuersWithCertificates.length) {
        const activeIssuer = issuersWithCertificates.find((issuer) => issuer.is_active) || issuersWithCertificates[0];
        setSelectedIssuerId(activeIssuer.id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'No fue posible cargar la certificación DGII.');
    } finally {
      setLoading(false);
    }
  }, [selectedIssuerId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleXmlChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.xml')) {
      notify.error('Archivo inválido', 'Debe seleccionar un archivo .xml.');
      event.target.value = '';
      return;
    }
    if (file.size > MAX_XML_BYTES) {
      notify.error('Archivo muy grande', 'El XML de postulación no puede exceder 2 MB.');
      event.target.value = '';
      return;
    }
    try {
      const content = await file.text();
      const info = getXmlInfo(file, content);
      setXmlFile(file);
      setXmlInfo(info);
      setSignedXml('');
      updateApplicationState('xml_generated');
      notify.success('XML cargado', 'La postulación está lista para firmarse.');
    } catch (err) {
      notify.error('XML inválido', err.message || 'Revise el archivo seleccionado.');
      event.target.value = '';
    }
  };

  const handleImportSet = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith('.xlsx') && !lowerName.endsWith('.xls')) {
      notify.error('Archivo inválido', 'Debe seleccionar un archivo .xlsx o .xls.');
      event.target.value = '';
      return;
    }
    if (file.size > MAX_EXCEL_BYTES) {
      notify.error('Archivo muy grande', 'El set DGII no puede exceder 5 MB.');
      event.target.value = '';
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    setImportingSet(true);
    try {
      const response = await api.post('/ecf/certification-plans/import-set/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPlans((current) => [response.data, ...current.filter((plan) => plan.id !== response.data.id)]);
      setActiveStep(2);
      notify.success('Set DGII importado', `${response.data.total_items || 0} escenarios detectados.`);
    } catch (err) {
      notify.error('No se pudo importar', err.response?.data?.detail || 'Revise el formato del Excel DGII.');
    } finally {
      setImportingSet(false);
      event.target.value = '';
    }
  };

  const importCommercialApprovalsFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      notify.error('Archivo inválido', 'Debe seleccionar el Excel .xlsx de aprobaciones comerciales DGII.');
      return;
    }
    if (file.size > MAX_EXCEL_BYTES) {
      notify.error('Archivo muy grande', 'El Excel DGII no puede exceder 5 MB.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    setImportingCommercialApprovals(true);
    try {
      const response = await api.post('/ecf/certification-commercial-approvals/import/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const latestResponse = await api.get('/ecf/certification-commercial-approvals/latest/');
      setCommercialApprovalPlan(latestResponse.data);
      const summary = response.data || {};
      if (summary.not_found || summary.ambiguous) {
        notify.warning('Aprobaciones importadas', 'Se encontraron registros sin coincidencia local.');
      } else {
        notify.success('Aprobaciones importadas correctamente.', `${summary.total || 0} registros procesados.`);
      }
    } catch (err) {
      notify.error('No se pudo importar', err.response?.data?.detail || 'Revise el Excel de aprobaciones comerciales DGII.');
    } finally {
      setImportingCommercialApprovals(false);
    }
  };

  const handleImportCommercialApprovals = async (event) => {
    const file = event.target.files?.[0];
    await importCommercialApprovalsFile(file);
    event.target.value = '';
  };

  const handleOpenCommercialApprovalsDialog = async () => {
    const result = await Swal.fire({
      title: commercialApprovalPlan ? 'Reemplazar Excel' : 'Seleccionar Excel',
      text: 'Seleccione el archivo oficial de Aprobaciones Comerciales DGII.',
      input: 'file',
      inputAttributes: {
        accept: '.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'aria-label': 'Excel de aprobaciones comerciales DGII',
      },
      showCancelButton: true,
      confirmButtonText: 'Procesar aprobaciones',
      cancelButtonText: 'Cancelar',
      reverseButtons: true,
    });
    if (result.isConfirmed && result.value) {
      await importCommercialApprovalsFile(result.value);
    }
  };

  const handleSubmitCommercialApprovals = async (planId) => {
    setGeneratingXml('submit-commercial-approvals');
    try {
      const response = await api.post(`/ecf/certification-commercial-approvals/${planId}/submit-dgii/`);
      setCommercialApprovalPlan(response.data?.plan || null);
      const summary = response.data?.summary || {};
      notify.success(
        'Aprobaciones enviadas',
        `${summary.accepted || 0} aceptadas por DGII, ${summary.rejected || 0} rechazadas.`,
      );
    } catch (err) {
      const detail = err.response?.data?.summary?.detail || err.response?.data?.detail;
      notify.error('No fue posible enviar aprobaciones comerciales', detail || 'Revise el contrato oficial de Aprobación Comercial.');
      if (err.response?.data?.plan) {
        setCommercialApprovalPlan(err.response.data.plan);
      }
    } finally {
      setGeneratingXml('');
    }
  };

  const handleSignXml = async () => {
    if (!selectedIssuer) {
      notify.warning('Seleccione un emisor', 'Debe elegir el emisor fiscal antes de firmar.');
      return;
    }
    if (!xmlFile) {
      notify.warning('Cargue el XML', 'Debe seleccionar el XML generado por el portal DGII.');
      return;
    }
    const formData = new FormData();
    formData.append('xml', xmlFile);
    setSigning(true);
    try {
      const response = await api.post(
        `/ecf/issuers/${selectedIssuer.id}/sign-certification-xml/`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      setSignedXml(response.data?.signed_xml || '');
      setSignedFilename(response.data?.filename || 'postulacion-dgii-firmado.xml');
      updateApplicationState('xml_signed');
      if (response.data?.warnings?.length) {
        notify.warning('XML firmado con advertencias', response.data.warnings[0]);
      } else {
        notify.success('XML firmado', 'El XML firmado está listo para descargar.');
      }
    } catch (err) {
      notify.error('No se pudo firmar', err.response?.data?.detail || 'Revise el certificado del emisor.');
    } finally {
      setSigning(false);
    }
  };

  const replacePlan = (updatedPlan) => {
    if (!updatedPlan) return;
    setPlans((current) => [updatedPlan, ...current.filter((plan) => plan.id !== updatedPlan.id)]);
  };

  const handleGenerateItemXml = async (planId, itemId) => {
    setGeneratingXml(`item-${itemId}`);
    try {
      const response = await api.post(`/ecf/certification-plans/${planId}/items/${itemId}/generate-xml/`);
      setPlans((current) => current.map((plan) => (
        plan.id === planId
          ? { ...plan, items: (plan.items || []).map((item) => (item.id === itemId ? response.data : item)) }
          : plan
      )));
      notify.success('Escenario preparado', 'El escenario normalizado quedó listo para descargar.');
    } catch (err) {
      const itemPayload = err.response?.data;
      if (itemPayload?.id) {
        setPlans((current) => current.map((plan) => (
          plan.id === planId
            ? { ...plan, items: (plan.items || []).map((item) => (item.id === itemId ? itemPayload : item)) }
            : plan
        )));
      }
      notify.error('No se pudo preparar el escenario', itemPayload?.generation_error || itemPayload?.detail || 'Revise el escenario DGII.');
    } finally {
      setGeneratingXml('');
    }
  };

  const handleGenerateGroupXml = async (planId, groupNumber) => {
    setGeneratingXml(`group-${groupNumber}`);
    try {
      const response = await api.post(`/ecf/certification-plans/${planId}/groups/${groupNumber}/generate-xml/`);
      replacePlan(response.data?.plan);
      const summary = response.data?.summary || {};
      const message = `${summary.generated || 0} generados, ${summary.failed || 0} fallidos.`;
      if (summary.failed) {
        notify.warning('Grupo procesado con errores', message);
      } else {
        notify.success('Grupo preparado', message);
      }
    } catch (err) {
      notify.error('No se pudo preparar el grupo', err.response?.data?.detail || 'Revise el plan DGII.');
    } finally {
      setGeneratingXml('');
    }
  };

  const handleDownloadGeneratedXml = async (planId, item) => {
    try {
      const response = await api.get(
        `/ecf/certification-plans/${planId}/items/${item.id}/download-xml/`,
        { responseType: 'blob' },
      );
      const filename = item.generated_xml_path?.split('/').pop() || `${item.ecf_type}-${item.encf || item.id}.xml`;
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify.error('No se pudo descargar', err.response?.data?.detail || 'El escenario normalizado no está disponible.');
    }
  };

  const handleGenerateCertificationDocument = async (planId, itemId) => {
    setGeneratingXml(`document-${itemId}`);
    try {
      const response = await api.post(`/ecf/certification-plans/${planId}/items/${itemId}/generate-document/`);
      setPlans((current) => current.map((plan) => (
        plan.id === planId
          ? { ...plan, items: (plan.items || []).map((item) => (item.id === itemId ? response.data : item)) }
          : plan
      )));
      notify.success('Documento generado', 'El e-CF de certificación quedó listo para descargar.');
    } catch (err) {
      const itemPayload = err.response?.data;
      if (itemPayload?.id) {
        setPlans((current) => current.map((plan) => (
          plan.id === planId
            ? { ...plan, items: (plan.items || []).map((item) => (item.id === itemId ? itemPayload : item)) }
            : plan
        )));
      }
      const errorMessage = itemPayload?.certification_document?.generation_error
        || itemPayload?.generation_error
        || itemPayload?.detail
        || 'Revise el escenario DGII.';
      notify.error('No se pudo generar el documento', errorMessage);
    } finally {
      setGeneratingXml('');
    }
  };

  const handleDownloadCertificationDocumentXml = async (planId, item) => {
    try {
      const response = await api.get(
        `/ecf/certification-plans/${planId}/items/${item.id}/download-document-xml/`,
        { responseType: 'blob' },
      );
      const certDocument = item.certification_document;
      const filename = `${certDocument?.ecf_type || item.ecf_type}-${certDocument?.encf || item.encf || item.id}-certificacion.xml`;
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify.error('No se pudo descargar', err.response?.data?.detail || 'El documento e-CF no está disponible.');
    }
  };

  const handleSignCertificationDocument = async (planId, itemId) => {
    setGeneratingXml(`sign-${itemId}`);
    try {
      const response = await api.post(`/ecf/certification-plans/${planId}/items/${itemId}/sign-document/`);
      setPlans((current) => current.map((plan) => (
        plan.id === planId
          ? { ...plan, items: (plan.items || []).map((item) => (item.id === itemId ? response.data : item)) }
          : plan
      )));
      notify.success('Documento firmado', 'El XML firmado está listo para descargar.');
    } catch (err) {
      const itemPayload = err.response?.data;
      if (itemPayload?.id) {
        setPlans((current) => current.map((plan) => (
          plan.id === planId
            ? { ...plan, items: (plan.items || []).map((item) => (item.id === itemId ? itemPayload : item)) }
            : plan
        )));
      }
      const errorMessage = itemPayload?.certification_document?.signing_error
        || itemPayload?.detail
        || 'Revise el certificado activo del emisor.';
      notify.error('No se pudo firmar', errorMessage);
    } finally {
      setGeneratingXml('');
    }
  };

  const handleDownloadSignedDocumentXml = async (planId, item) => {
    try {
      const response = await api.get(
        `/ecf/certification-plans/${planId}/items/${item.id}/download-signed-xml/`,
        { responseType: 'blob' },
      );
      const certDocument = item.certification_document;
      const filename = `${certDocument?.ecf_type || item.ecf_type}-${certDocument?.encf || item.encf || item.id}-firmado.xml`;
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify.error('No se pudo descargar', err.response?.data?.detail || 'El XML firmado no está disponible.');
    }
  };

  const handleDownloadSignedGroupZip = async (planId, groupNumber) => {
    setGeneratingXml(`download-signed-zip-${groupNumber}`);
    try {
      const response = await api.get(
        `/ecf/certification-plans/${planId}/groups/${groupNumber}/download-signed-zip/`,
        { responseType: 'blob' },
      );
      const filename = `plan-${planId}-grupo-${groupNumber}-xml-firmados.zip`;
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify.error('No se pudo descargar el ZIP', err.response?.data?.detail || 'El grupo no tiene XML firmados disponibles.');
    } finally {
      setGeneratingXml('');
    }
  };

  const handleSubmitItemDgii = async (planId, item) => {
    const isRfce = item.ecf_type === 'RFCE';
    const confirmed = await confirmDgiiAction(
      isRfce
        ? {
            title: 'Enviar RFCE',
            text: 'Se enviará este Resumen de Factura de Consumo Electrónica (RFCE) a la DGII. Una vez enviado, deberá esperar la respuesta de la DGII antes de continuar.',
            confirmButtonText: 'Enviar RFCE',
          }
        : {
            title: 'Enviar comprobante a DGII',
            text: `Se enviará el comprobante ${item.encf || item.id} a la DGII para su validación.`,
            confirmButtonText: 'Enviar a DGII',
          },
    );
    if (!confirmed) return;

    setGeneratingXml(`submit-item-${item.id}`);
    try {
      const response = await api.post(`/ecf/certification-plans/${planId}/items/${item.id}/submit-dgii/`);
      replacePlan(response.data?.plan);
      const summary = response.data?.summary || {};
      notify.success(
        isRfce ? 'RFCE enviado a DGII' : 'Documento enviado a DGII',
        `${summary.submitted || 0} enviado, ${summary.accepted || 0} aceptado, ${summary.rejected || 0} rechazado.`,
      );
    } catch (err) {
      const firstError = err.response?.data?.summary?.errors?.[0];
      const detail = err.response?.data?.detail || firstError?.dgii_error?.response_text || firstError?.error;
      notify.error(isRfce ? 'No se pudo enviar el RFCE' : 'No se pudo enviar el documento', detail || 'Revise la respuesta DGII.');
      if (err.response?.data?.plan) {
        replacePlan(err.response.data.plan);
      }
    } finally {
      setGeneratingXml('');
    }
  };

  const handleUpdatePortalStatus = async (planId, item, statusValue) => {
    setGeneratingXml(`portal-status-${item.id}`);
    try {
      const response = await api.post(
        `/ecf/certification-plans/${planId}/items/${item.id}/portal-status/`,
        { status: statusValue },
      );
      replacePlan(response.data?.plan);
      notify.success('Estado actualizado', 'El resultado confirmado en portal quedó registrado.');
    } catch (err) {
      notify.error('No se pudo actualizar', err.response?.data?.detail || 'Revise el estado del documento.');
    } finally {
      setGeneratingXml('');
    }
  };

  const handleRunDataTests = async (planId) => {
    const confirmed = await confirmDgiiAction({
      title: 'Enviar pruebas de datos',
      text: 'Se procesarán secuencialmente los 21 comprobantes e-CF y luego los 4 RFCE. Si DGII rechaza un documento, el proceso se detendrá.',
      confirmButtonText: 'Enviar pruebas',
    });
    if (!confirmed) return;

    setGeneratingXml('run-data-tests');
    try {
      const response = await api.post(`/ecf/certification-plans/${planId}/data-tests/run/`);
      replacePlan(response.data?.plan);
      notify.success('Proceso completado', 'DGII aceptó los 21 e-CF y los 4 RFCE. Los XML íntegros quedan listos para portal.');
    } catch (err) {
      const summary = err.response?.data?.summary || {};
      const detail = err.response?.data?.detail || summary.message;
      notify.error('Proceso detenido', detail || 'Revise el e-NCF fallido y el mensaje DGII.');
      if (err.response?.data?.plan) {
        replacePlan(err.response.data.plan);
      }
    } finally {
      setGeneratingXml('');
    }
  };

  const recommendation = (() => {
    const status = activeCertificate?.status || selectedIssuer?.certificate_status;
    if (!selectedIssuer) return 'Configure un emisor fiscal en Empresa antes de iniciar la certificación.';
    if (!status || status === 'missing') return 'Obtenga y cargue el certificado digital DGII del contribuyente.';
    if (status === 'invalid' || status === 'expired') return 'Corrija el certificado antes de firmar la postulación.';
    if (!xmlInfo) return 'Genere el XML de postulación en el portal DGII y cárguelo aquí.';
    if (!signedXml) return 'Firme el XML de postulación con el certificado activo del emisor.';
    if (applicationState === 'xml_signed') return 'Suba el XML firmado al portal DGII y marque el envío cuando corresponda.';
    if (applicationState === 'sent_to_dgii') return 'Espere la aprobación de DGII y registre el resultado visualmente.';
    return 'Continúe con el proceso de certificación indicado por DGII.';
  })();
  const activeFlowStep = certificationFlowSteps.find((step) => step.id === activeStep) || certificationFlowSteps[0];

  if (loading) {
    return (
      <section className="dgii-wizard-page">
        <div className="dgii-wizard-loading">Cargando certificación DGII...</div>
      </section>
    );
  }

  return (
    <section className="dgii-wizard-page">
      <header className="dgii-wizard-header dgii-assistant-header">
        <div>
          <p className="dgii-wizard-eyebrow">Empresa / Certificación DGII</p>
          <h1>Certificación DGII</h1>
          <p>Asistente operativo para avanzar el flujo de certificación e-CF sin afectar la emisión normal.</p>
        </div>
        <div className="dgii-assistant-header-actions">
          <button type="button" className="dgii-wizard-secondary" onClick={loadData}>
            Actualizar estado
          </button>
        </div>
      </header>

      {error && (
        <div className="dgii-wizard-alert danger">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="dgii-assistant-shell">
        <aside className="dgii-assistant-sidebar" aria-label="Flujo certificación DGII">
          <div className="dgii-assistant-sidebar-title">
            <strong>Flujo certificación</strong>
            <span>{activeFlowStep.id}/15</span>
          </div>
          <div className="dgii-assistant-steps">
            {certificationFlowSteps.map((step) => (
              <button
                key={step.id}
                type="button"
                className={`dgii-assistant-step ${step.id === activeStep ? 'active' : ''} ${step.id < activeStep ? 'visited' : ''}`}
                onClick={() => setActiveStep(step.id)}
              >
                <span>{step.id}</span>
                <strong>{step.title}</strong>
              </button>
            ))}
          </div>
        </aside>

        <main className="dgii-assistant-panel">
          {activeStep === 1 && (
            <div className="dgii-assistant-step-content">
              <article className="dgii-wizard-card">
                <div className="dgii-wizard-card-header">
                  <div>
                    <h2>Emisor fiscal</h2>
                    <p>{company?.name || 'Empresa activa'} · RNC {company?.rnc || selectedIssuer?.rnc || 'No disponible'}</p>
                  </div>
                  <ShieldCheck size={22} />
                </div>

                {issuers.length === 0 ? (
                  <div className="dgii-wizard-empty">No hay emisor fiscal configurado para esta empresa.</div>
                ) : (
                  <>
                    <label className="dgii-wizard-field">
                      Emisor fiscal
                      <select value={selectedIssuerId} onChange={(event) => setSelectedIssuerId(event.target.value)}>
                        {issuers.map((issuer) => (
                          <option key={issuer.id} value={issuer.id}>
                            {issuer.business_name || issuer.trade_name || issuer.rnc} · RNC {issuer.rnc}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
              </article>

              <article className="dgii-wizard-card">
                <div className="dgii-wizard-card-header">
                  <div>
                    <h2>Postulación</h2>
                    <p>Firma el XML descargado del portal DGII.</p>
                  </div>
                  <FileSignature size={22} />
                </div>
                <div className="dgii-application-state-row">
                  {applicationStates.map((state, index) => {
                    const currentIndex = applicationStates.findIndex((item) => item.value === applicationState);
                    const done = index <= currentIndex;
                    return (
                      <button
                        key={state.value}
                        type="button"
                        className={`dgii-application-pill ${done ? 'done' : ''} ${state.value === applicationState ? 'current' : ''}`}
                        onClick={() => updateApplicationState(state.value)}
                      >
                        {state.label}
                      </button>
                    );
                  })}
                </div>

                <div className="dgii-wizard-upload">
                  <label className="dgii-wizard-file">
                    <input type="file" accept=".xml,application/xml,text/xml" onChange={handleXmlChange} />
                    <FileUp size={18} />
                    Seleccionar XML postulación
                  </label>
                  <button
                    type="button"
                    className="dgii-wizard-primary"
                    disabled={!xmlFile || !selectedIssuer || signing}
                    onClick={handleSignXml}
                  >
                    <FileSignature size={18} />
                    {signing ? 'Firmando...' : 'Firmar XML'}
                  </button>
                  <button
                    type="button"
                    className="dgii-wizard-secondary"
                    disabled={!signedXml}
                    onClick={() => downloadTextFile(signedFilename, signedXml)}
                  >
                    <Download size={18} />
                    Descargar XML firmado
                  </button>
                </div>

                {xmlInfo && (
                  <div className="dgii-wizard-xml-info compact">
                    <div><span>Archivo</span><strong>{xmlInfo.filename}</strong></div>
                    <div><span>Raíz</span><strong>{xmlInfo.rootName}</strong></div>
                    <div><span>Tamaño</span><strong>{Math.ceil(xmlInfo.size / 1024)} KB</strong></div>
                    <div><span>Cargado</span><strong>{formatDate(xmlInfo.uploadedAt, true)}</strong></div>
                  </div>
                )}
              </article>

              <article className="dgii-wizard-card dgii-assistant-side-card">
                <div className="dgii-wizard-card-header">
                  <div>
                    <h2>Guía</h2>
                    <p>Siguiente acción sugerida.</p>
                  </div>
                  <Info size={22} />
                </div>
                <div className="dgii-wizard-recommendation">{recommendation}</div>
                <div className="dgii-wizard-links compact">
                  <a href="https://ecf.dgii.gov.do/certecf/portalcertificacion" target="_blank" rel="noreferrer">
                    Portal certificación DGII
                  </a>
                  <a href="https://ra.viafirma.do" target="_blank" rel="noreferrer">
                    Solicitud certificado Viafirma
                  </a>
                  <a href={process.env.REACT_APP_DGII_DOCS_URL || 'https://dgii.gov.do'} target="_blank" rel="noreferrer">
                    Documentación DGII <ExternalLink size={14} />
                  </a>
                </div>
              </article>
            </div>
          )}

          {activeStep === 2 && (
            <DGIICertificationTestsSection
              selectedIssuer={selectedIssuer}
              importingSet={importingSet}
              generatingXml={generatingXml}
              latestPlan={latestPlan}
              onImportSet={handleImportSet}
              onGenerateItemXml={handleGenerateItemXml}
              onGenerateGroupXml={handleGenerateGroupXml}
              onDownloadGeneratedXml={handleDownloadGeneratedXml}
              onGenerateCertificationDocument={handleGenerateCertificationDocument}
              onDownloadCertificationDocumentXml={handleDownloadCertificationDocumentXml}
              onSignCertificationDocument={handleSignCertificationDocument}
              onDownloadSignedDocumentXml={handleDownloadSignedDocumentXml}
              onDownloadSignedGroupZip={handleDownloadSignedGroupZip}
              onRunDataTests={handleRunDataTests}
              onSubmitItemDgii={handleSubmitItemDgii}
              onUpdatePortalStatus={handleUpdatePortalStatus}
              onNextStep={() => setActiveStep(3)}
            />
          )}

          {activeStep === 3 && (
            <DGIICertificationCommercialApprovalsSection
              plan={commercialApprovalPlan}
              importing={importingCommercialApprovals}
              submitting={generatingXml === 'submit-commercial-approvals'}
              onImport={handleImportCommercialApprovals}
              onOpenImportDialog={handleOpenCommercialApprovalsDialog}
              onSubmitApprovals={handleSubmitCommercialApprovals}
              onNextStep={() => setActiveStep(4)}
            />
          )}

          {activeStep > 3 && (
            <>
              <div className="dgii-assistant-panel-header">
                <div>
                  <p className="dgii-wizard-eyebrow">Paso {activeFlowStep.id}</p>
                  <h2>{activeFlowStep.title}</h2>
                </div>
                <button type="button" className="dgii-wizard-secondary" onClick={() => setActiveStep(Math.min(activeStep + 1, 15))}>
                  Siguiente paso
                </button>
              </div>
              <div className="dgii-assistant-placeholder">
                <FileCheck2 size={28} />
                <h3>{activeFlowStep.title}</h3>
                <p>Este paso queda visible para orientar el flujo DGII. Su operación se habilitará en una fase posterior sin mezclarla con la facturación productiva.</p>
              </div>
            </>
          )}
        </main>
      </div>
    </section>
  );
}

function DGIICertificationTestsSection({
  selectedIssuer,
  importingSet,
  generatingXml,
  latestPlan,
  onImportSet,
  onSignCertificationDocument,
  onDownloadSignedDocumentXml,
  onDownloadSignedGroupZip,
  onRunDataTests,
  onSubmitItemDgii,
  onUpdatePortalStatus,
  onNextStep,
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [groupTab, setGroupTab] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const groupCounts = latestPlan?.group_counts || {};
  const allItems = latestPlan?.items || [];
  const groups = [
    { id: '1', title: 'Grupo 1', detail: '31, 32 >= 250,000, 41, 43, 44, 45, 46, 47' },
    { id: '2', title: 'Grupo 2', detail: '33, 34' },
    { id: '3', title: 'Grupo 3', detail: 'RFCE / Resúmenes de consumo' },
    { id: '4', title: 'Grupo 4', detail: '32 < 250,000' },
  ];
  const groupsWithStats = groups.map((group) => {
    const items = allItems.filter((item) => String(item.dgii_group) === String(group.id));
    const fallbackTotal = groupCounts[group.id] || 0;
    return {
      ...group,
      items,
      stats: statsWithFallback(items, fallbackTotal),
    };
  });
  const selectedItem = allItems.find((item) => String(item.id) === String(selectedItemId));
  const dataEcfItems = allItems.filter((item) => ['1', '2'].includes(String(item.dgii_group)));
  const dataEcfPendingResendCount = dataEcfItems.filter(isPendingResendItem).length;
  const dataEcfAcceptedCount = dataEcfPendingResendCount > 0 ? 0 : dataEcfItems.filter(isAcceptedItem).length;
  const dataEcfRejectedCount = dataEcfItems.filter(isRejectedItem).length;
  const dataEcfConflictCount = dataEcfItems.filter((item) => item.certification_document?.status === 'submit_conflict').length;
  const dataEcfPendingCount = Math.max(dataEcfItems.length - dataEcfAcceptedCount - dataEcfRejectedCount - dataEcfConflictCount, 0);
  const dataEcfProgress = dataEcfItems.length ? Math.round((dataEcfAcceptedCount / dataEcfItems.length) * 100) : 0;
  const rfceItems = groupsWithStats.find((group) => group.id === '3')?.items || [];
  const rfceStats = groupsWithStats.find((group) => group.id === '3')?.stats || statsWithFallback([], 4);
  const rfceAcceptedCount = rfceItems.filter(isAcceptedItem).length;
  const lowConsumptionItems = groupsWithStats.find((group) => group.id === '4')?.items || [];
  const lowConsumptionSignedCount = lowConsumptionItems.filter(hasSignedXml).length;
  const lowConsumptionPortalUploadedCount = lowConsumptionItems.filter((item) => (
    ['uploaded_to_portal', 'accepted_by_portal'].includes(item.certification_document?.status)
  )).length;
  const lowConsumptionPortalAcceptedCount = lowConsumptionItems.filter((item) => (
    item.certification_document?.status === 'accepted_by_portal'
  )).length;
  const lowConsumptionTotal = lowConsumptionItems.length || Number(groupCounts['4'] || 0) || 4;
  const visualGroups = [
    {
      id: 'data-ecf',
      title: 'Grupo 1 — Datos e-CF',
      detail: 'Incluye los grupos internos DGII 1 + 2',
      countLabel: '21 comprobantes',
      items: dataEcfItems,
      stats: {
        ...getGroupStats(dataEcfItems),
        total: 21,
        accepted: dataEcfAcceptedCount,
        pendingResend: dataEcfPendingResendCount,
        rejected: dataEcfRejectedCount,
        conflicts: dataEcfConflictCount,
        pending: dataEcfPendingCount,
        progress: dataEcfProgress,
        complete: dataEcfAcceptedCount === 21 && dataEcfPendingResendCount === 0,
      },
      type: 'data-ecf',
    },
    {
      id: '3',
      backendGroupNumber: '3',
      title: 'Grupo 2 — RFCE / Resúmenes de consumo',
      detail: 'Incluye los 4 RFCE',
      countLabel: '4 resúmenes',
      items: rfceItems,
      stats: rfceStats,
      type: 'rfce',
    },
    {
      id: '4',
      backendGroupNumber: '4',
      title: 'Grupo 3 — Facturas consumo <250K',
      detail: 'XML íntegros para carga manual en portal DGII',
      countLabel: '4 comprobantes',
      items: lowConsumptionItems,
      stats: {
        ...(groupsWithStats.find((group) => group.id === '4')?.stats || statsWithFallback([], 4)),
        total: lowConsumptionTotal,
        accepted: lowConsumptionPortalAcceptedCount,
        uploadedToPortal: lowConsumptionPortalUploadedCount,
        signed: lowConsumptionSignedCount,
        pending: Math.max(lowConsumptionTotal - lowConsumptionPortalUploadedCount, 0),
        rejected: 0,
        conflicts: 0,
        pendingResend: 0,
        progress: lowConsumptionTotal ? Math.round((lowConsumptionPortalAcceptedCount / lowConsumptionTotal) * 100) : 0,
        complete: false,
        canSubmit: false,
        canPrepare: lowConsumptionTotal > 0 && lowConsumptionSignedCount < lowConsumptionTotal,
      },
      type: 'low-consumption',
    },
  ];

  const filteredItems = allItems.filter((item) => {
    if (groupTab === 'data-ecf' && !['1', '2'].includes(String(item.dgii_group))) return false;
    if (groupTab !== 'all' && groupTab !== 'data-ecf' && String(item.dgii_group) !== groupTab) return false;
    if (statusFilter === 'accepted' && !isAcceptedItem(item)) return false;
    if (statusFilter === 'rejected' && !isRejectedItem(item)) return false;
    if (statusFilter === 'pending' && (isAcceptedItem(item) || isRejectedItem(item))) return false;
    if (searchTerm && !(item.encf || '').toLowerCase().includes(searchTerm.trim().toLowerCase())) return false;
    return true;
  });
  const visibleItems = filteredItems.slice(0, visibleCount);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [groupTab, statusFilter, searchTerm, latestPlan?.id]);

  const unifiedStageLabel = (() => {
    if (generatingXml === 'run-data-tests') return 'Procesando pruebas de datos';
    if (String(generatingXml).startsWith('documents-group-')) return 'Preparando documentos';
    if (String(generatingXml).startsWith('sign-group-')) return 'Firmando documentos';
    return '';
  })();

  return (
    <div className="dgii-tests-layout">
      <section className="dgii-tests-main">
        <article className="dgii-wizard-card dgii-tests-excel-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Excel DGII</h2>
              <p>{latestPlan?.source_filename || 'Sin archivo importado'} · {latestPlan?.total_items || 0} escenarios · {formatDate(latestPlan?.imported_at, true)}</p>
            </div>
            <FileUp size={22} />
          </div>
          <label className="dgii-wizard-file">
            <input type="file" accept=".xlsx,.xls" onChange={onImportSet} disabled={importingSet} />
            <FileUp size={18} />
            {importingSet ? 'Importando...' : latestPlan ? 'Reemplazar Excel' : 'Importar Excel DGII'}
          </label>
        </article>

        <article className="dgii-wizard-card dgii-advanced-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Grupos detectados</h2>
              <p>Procesa por grupo y revisa resultados antes de continuar.</p>
            </div>
            <button type="button" className="dgii-wizard-mini-action secondary" onClick={onNextStep}>
              Siguiente paso
            </button>
          </div>
          <div className="dgii-group-actions">
            <button
              type="button"
              className="dgii-wizard-primary"
              disabled={!latestPlan || Boolean(generatingXml)}
              onClick={() => onRunDataTests(latestPlan.id)}
            >
              {generatingXml === 'run-data-tests' ? 'Procesando...' : 'Enviar pruebas de datos'}
            </button>
            {unifiedStageLabel && <strong className="dgii-group-completed-label">{unifiedStageLabel}</strong>}
          </div>
          <div className="dgii-certification-groups guided">
            {visualGroups.map((group) => {
              const isDataEcf = group.type === 'data-ecf';
              const isRfce = group.type === 'rfce';
              const isLowConsumption = group.type === 'low-consumption';
              const needsResubmit = (group.stats.pendingResend || 0) > 0;
              return (
              <div key={group.id} className={`${group.stats.complete && !needsResubmit ? 'complete' : ''} ${isDataEcf ? 'data-ecf-main' : ''}`}>
                <div className="dgii-group-compact-head">
                  <strong>{group.title}</strong>
                  <b>{group.stats.accepted || 0}/{group.stats.total || 0}</b>
                </div>
                <span>{group.detail} · {group.countLabel}</span>
                <div className="dgii-group-progress">
                  <span style={{ width: `${group.stats.progress}%` }} />
                </div>
                <div className="dgii-group-summary-line">
                  {isLowConsumption ? (
                    <>
                      <em className="ok">Aceptadas en portal: {group.stats.accepted}/{group.stats.total}</em>
                    </>
                  ) : (
                    <>
                      <em className="ok">{group.stats.accepted} aceptados</em>
                      {group.stats.rejected > 0 && <em className="err">{group.stats.rejected} rechazados</em>}
                      {group.stats.conflicts > 0 && <em>{group.stats.conflicts} secuencia usada</em>}
                      {group.stats.pendingResend > 0 && <em>{group.stats.pendingResend} requieren reenvío</em>}
                      <em>{group.stats.pending + group.stats.submitted} pendientes</em>
                    </>
                  )}
                </div>
                {needsResubmit && <strong className="dgii-group-completed-label">Requiere reenvío</strong>}
                {group.stats.complete && !needsResubmit ? (
                  <strong className="dgii-group-completed-label">Grupo completado</strong>
                ) : isDataEcf ? (
                  <div className="dgii-group-actions">
                    <button type="button" className="dgii-wizard-mini-action secondary" onClick={() => setGroupTab('data-ecf')}>
                      Ver detalle
                    </button>
                  </div>
                ) : isRfce ? (
                  <div className="dgii-group-actions">
                    <button type="button" className="dgii-wizard-mini-action secondary" onClick={() => setGroupTab(group.id)}>
                      Ver detalle
                    </button>
                  </div>
                ) : isLowConsumption ? (
                  <div className="dgii-group-actions">
                    <button
                      type="button"
                      className="dgii-wizard-mini-action secondary"
                      disabled={
                        !latestPlan
                        || rfceAcceptedCount !== 4
                        || (group.stats.signed || 0) === 0
                        || generatingXml === `download-signed-zip-${group.backendGroupNumber}`
                      }
                      onClick={() => onDownloadSignedGroupZip(latestPlan.id, group.backendGroupNumber)}
                    >
                      {generatingXml === `download-signed-zip-${group.backendGroupNumber}` ? 'Descargando...' : 'Descargar ZIP'}
                    </button>
                    <button type="button" className="dgii-wizard-mini-action secondary" onClick={() => setGroupTab(group.id)}>
                      Ver detalle
                    </button>
                  </div>
                ) : null}
              </div>
              );
            })}
          </div>
        </article>

        <article className="dgii-wizard-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Resultados</h2>
              <p>{filteredItems.length} de {allItems.length} escenarios</p>
            </div>
          </div>

          {!latestPlan ? (
            <div className="dgii-wizard-empty">Aún no hay plan de certificación importado para esta empresa.</div>
          ) : (
            <>
              <div className="dgii-filter-bar">
                <div className="dgii-search-box">
                  <Search size={15} />
                  <input
                    type="text"
                    placeholder="Buscar e-NCF..."
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                  />
                </div>
                <div className="dgii-filter-pills">
                  <button type="button" className={groupTab === 'all' ? 'active' : ''} onClick={() => setGroupTab('all')}>Todos los grupos</button>
                  {visualGroups.map((group) => (
                    <button key={group.id} type="button" className={groupTab === group.id ? 'active' : ''} onClick={() => setGroupTab(group.id)}>
                      {group.title}
                    </button>
                  ))}
                </div>
                <div className="dgii-filter-pills">
                  <button type="button" className={statusFilter === 'all' ? 'active' : ''} onClick={() => setStatusFilter('all')}>Todos</button>
                  <button type="button" className={statusFilter === 'accepted' ? 'active' : ''} onClick={() => setStatusFilter('accepted')}>Aceptados</button>
                  <button type="button" className={statusFilter === 'pending' ? 'active' : ''} onClick={() => setStatusFilter('pending')}>Pendientes</button>
                  <button type="button" className={statusFilter === 'rejected' ? 'active' : ''} onClick={() => setStatusFilter('rejected')}>Rechazados</button>
                </div>
              </div>

              <div className="dgii-certification-table-wrap">
                <table className="dgii-certification-table compact">
                  <thead>
                    <tr>
                      <th>e-NCF</th>
                      <th>Tipo</th>
                      <th>Estado</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleItems.map((item) => (
                      <tr key={item.id} className={String(item.id) === String(selectedItemId) ? 'selected' : ''}>
                        <td data-label="e-NCF">{item.encf || 'No detectado'}</td>
                        <td data-label="Tipo">{item.ecf_type} · {item.ecf_type_label}</td>
                        <td data-label="Estado">{statusBadge(certificationStatusMeta(item))}</td>
                        <td data-label="Acción">
                          <button
                            type="button"
                            className="dgii-wizard-mini-action secondary"
                            onClick={() => setSelectedItemId(item.id)}
                          >
                            Ver detalle
                          </button>
                        </td>
                      </tr>
                    ))}
                    {visibleItems.length === 0 && (
                      <tr>
                        <td colSpan={4} className="dgii-table-empty-row">Sin resultados para este filtro.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {filteredItems.length > visibleItems.length && (
                <button type="button" className="dgii-wizard-secondary dgii-table-more" onClick={() => setVisibleCount((count) => count + PAGE_SIZE)}>
                  Mostrar más ({filteredItems.length - visibleItems.length} restantes)
                </button>
              )}
            </>
          )}

          {selectedItem && (
            <div className="dgii-tests-detail">
              <div className="dgii-wizard-card-header">
                <div>
                  <h2>{selectedItem.encf || 'Detalle'}</h2>
                  <p>{selectedItem.ecf_type_label || selectedItem.ecf_type}</p>
                </div>
                <button type="button" className="dgii-wizard-mini-action secondary" onClick={() => setSelectedItemId(null)}>
                  Cerrar
                </button>
              </div>
              <div className="dgii-tests-detail-grid">
                <div><span>Monto</span><strong>{selectedItem.amount || 'No disponible'}</strong></div>
                <div><span>Receptor</span><strong>{selectedItem.receiver_name || selectedItem.receiver_rnc || 'No disponible'}</strong></div>
                <div><span>Origen</span><strong>{selectedItem.source_sheet} · fila {selectedItem.source_row}</strong></div>
                <div><span>TrackID</span><strong>{selectedItem.certification_document?.dgii_track_id || 'No disponible'}</strong></div>
                <div><span>Filename</span><strong>{selectedItem.certification_document?.encf ? `${selectedIssuer?.rnc || ''}${selectedItem.certification_document.encf}.xml` : 'No disponible'}</strong></div>
                <div><span>Hash firmado</span><strong>{compact(selectedItem.certification_document?.signed_xml_hash, 36)}</strong></div>
              </div>
              <p className="dgii-tests-full-message">{dgiiShortMessage(selectedItem)}</p>
              <button
                type="button"
                className="dgii-wizard-mini-action secondary"
                disabled={!hasSignedXml(selectedItem) || (String(selectedItem.dgii_group) === '4' && rfceAcceptedCount !== 4)}
                onClick={() => onDownloadSignedDocumentXml(latestPlan.id, selectedItem)}
                title={String(selectedItem.dgii_group) === '4' && rfceAcceptedCount !== 4 ? 'Debe reenviar y aceptar los 4 RFCE antes de descargar XML íntegros para el portal.' : undefined}
              >
                Descargar XML firmado
              </button>
              {selectedItem.ecf_type === 'RFCE' && (
                <button
                  type="button"
                  className="dgii-wizard-mini-action danger"
                  disabled={!hasSignedXml(selectedItem) || generatingXml}
                  onClick={() => onSubmitItemDgii(latestPlan.id, selectedItem)}
                >
                  {generatingXml === `submit-item-${selectedItem.id}` ? 'Enviando...' : 'Enviar 1 RFCE'}
                </button>
              )}
              {String(selectedItem.dgii_group) === '4' && (
                <>
                  <button
                    type="button"
                    className="dgii-wizard-mini-action secondary"
                    disabled={generatingXml === `portal-status-${selectedItem.id}`}
                    onClick={() => onUpdatePortalStatus(latestPlan.id, selectedItem, 'uploaded_to_portal')}
                  >
                    Registrar cargada en portal
                  </button>
                  <button
                    type="button"
                    className="dgii-wizard-mini-action secondary"
                    disabled={generatingXml === `portal-status-${selectedItem.id}`}
                    onClick={() => onUpdatePortalStatus(latestPlan.id, selectedItem, 'accepted_by_portal')}
                  >
                    Registrar aceptada en portal
                  </button>
                </>
              )}
            </div>
          )}
        </article>

        <article className="dgii-wizard-card">
          <button
            type="button"
            className="dgii-advanced-toggle"
            onClick={() => setAdvancedOpen((value) => !value)}
          >
            {advancedOpen ? 'Ocultar opciones avanzadas' : 'Opciones avanzadas'}
          </button>
          {advancedOpen && latestPlan && (
            <div className="dgii-advanced-panel">
              <div className="dgii-advanced-panel-block">
                <strong>Acciones técnicas ocultas</strong>
                <span className="dgii-advanced-hint">
                  La operación por grupo se realiza con Preparar grupo y Enviar grupo. Las acciones manuales individuales quedan fuera de la vista principal para evitar reprocesos accidentales.
                </span>
              </div>
            </div>
          )}
        </article>

      </section>
    </div>
  );
}

function DGIICertificationCommercialApprovalsSection({
  plan,
  importing,
  submitting,
  onImport,
  onOpenImportDialog,
  onSubmitApprovals,
  onNextStep,
}) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItemId, setSelectedItemId] = useState(null);
  const items = plan?.items || [];
  const filteredItems = items.filter((item) => {
    if (statusFilter === 'approved' && item.source_approval_status !== 'approved') return false;
    if (statusFilter === 'rejected' && item.source_approval_status !== 'rejected') return false;
    if (statusFilter === 'pending' && item.submission_status !== 'pending') return false;
    if (statusFilter === 'not_found' && item.match_status !== 'not_found') return false;
    const search = searchTerm.trim().toLowerCase();
    if (search && !`${item.encf || ''} ${item.issuer_rnc || ''} ${item.buyer_rnc || ''}`.toLowerCase().includes(search)) {
      return false;
    }
    return true;
  });
  const selectedItem = items.find((item) => String(item.id) === String(selectedItemId));
  const summary = plan?.raw_summary || {};
  const submissionSummary = plan?.submission_summary || {};
  const canContinue = Boolean(plan?.is_step_complete && plan?.total_records > 0);

  const statusMeta = (statusValue) => {
    if (statusValue === 'aprobado') return { label: 'Aprobado', tone: 'success' };
    if (statusValue === 'rechazado') return { label: 'Rechazado', tone: 'danger' };
    if (statusValue === 'pendiente') return { label: 'Pendiente', tone: 'warning' };
    return { label: 'Desconocido', tone: 'neutral' };
  };

  const submissionMeta = (statusValue) => {
    if (statusValue === 'accepted') return { label: 'Aceptado DGII', tone: 'success' };
    if (statusValue === 'rejected') return { label: 'Rechazado DGII', tone: 'danger' };
    if (statusValue === 'failed') return { label: 'Fallido', tone: 'danger' };
    if (statusValue === 'submitted') return { label: 'Enviado', tone: 'info' };
    if (statusValue === 'signed') return { label: 'Firmado', tone: 'info' };
    if (statusValue === 'generated') return { label: 'Generado', tone: 'info' };
    return { label: 'Por enviar', tone: 'warning' };
  };

  const matchMeta = (matchStatus) => {
    if (matchStatus === 'matched') return { label: 'Coincide', tone: 'success' };
    if (matchStatus === 'ambiguous') return { label: 'Ambiguo', tone: 'warning' };
    if (matchStatus === 'not_found') return { label: 'No encontrada', tone: 'danger' };
    return { label: 'No aplica', tone: 'neutral' };
  };

  return (
    <div className="dgii-tests-layout">
      <section className="dgii-tests-main">
        <article className="dgii-wizard-card dgii-tests-excel-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Paso 3 — Pruebas de Datos Aprobación Comercial</h2>
              <p>Importa y procesa el resultado oficial entregado por DGII.</p>
            </div>
            <button
              type="button"
              className="dgii-wizard-mini-action secondary"
              disabled={!canContinue}
              onClick={onNextStep}
            >
              Siguiente paso
            </button>
          </div>
          <div className="dgii-wizard-upload">
            <button
              type="button"
              className="dgii-wizard-primary"
              disabled={importing}
              onClick={onOpenImportDialog}
            >
              <FileUp size={18} />
              {importing ? 'Procesando...' : plan ? 'Reemplazar Excel' : 'Seleccionar Excel'}
            </button>
            <label className="dgii-wizard-file dgii-commercial-hidden-file">
              <input type="file" accept=".xlsx" onChange={onImport} disabled={importing} />
              <FileUp size={18} />
              Carga alternativa
            </label>
          </div>
          {plan ? (
            <div className="dgii-wizard-xml-info compact">
              <div><span>Archivo</span><strong>{plan.source_filename}</strong></div>
              <div><span>Importado</span><strong>{formatDate(plan.imported_at, true)}</strong></div>
              <div><span>Total</span><strong>{plan.total_records}</strong></div>
              <div><span>DGII</span><strong>{submissionSummary.accepted_by_dgii || 0}/{plan.total_records} aceptadas</strong></div>
            </div>
          ) : (
            <div className="dgii-wizard-empty">No hay archivo de aprobaciones comerciales importado.</div>
          )}
        </article>

        {plan && (
          <>
            <article className="dgii-wizard-card">
              <div className="dgii-stat-strip">
                <div><span>Total</span><strong>{plan.total_records}</strong></div>
                <div className="ok"><span>Decisión aprobada</span><strong>{submissionSummary.source_approved || plan.approved_count}</strong></div>
                <div className="error"><span>Decisión rechazada</span><strong>{submissionSummary.source_rejected || plan.rejected_count}</strong></div>
                <div><span>Por enviar</span><strong>{submissionSummary.pending_submission || 0}</strong></div>
                <div className="ok"><span>Aceptadas DGII</span><strong>{submissionSummary.accepted_by_dgii || 0}</strong></div>
                <div className="error"><span>Fallidas</span><strong>{submissionSummary.failed || 0}</strong></div>
                <div className="ok"><span>Coincidencias</span><strong>{summary.matched || 0}</strong></div>
                <div className="error"><span>No encontradas</span><strong>{summary.not_found || 0}</strong></div>
              </div>
              <div className="dgii-group-actions dgii-mt-3">
                <button
                  type="button"
                  className="dgii-wizard-primary"
                  disabled={submitting || !plan.total_records}
                  onClick={() => onSubmitApprovals(plan.id)}
                >
                  {submitting ? 'Procesando...' : `Preparar y enviar ${plan.total_records} aprobaciones`}
                </button>
              </div>
              {(summary.not_found > 0 || summary.ambiguous > 0) && (
                <div className="dgii-wizard-alert warning dgii-mt-3">
                  <AlertTriangle size={18} />
                  <span>Hay registros sin coincidencia local o ambiguos. La importación se conserva para revisión.</span>
                </div>
              )}
            </article>

            <article className="dgii-wizard-card">
              <div className="dgii-wizard-card-header">
                <div>
                  <h2>Aprobaciones comerciales DGII</h2>
                  <p>{filteredItems.length} de {items.length} registros</p>
                </div>
              </div>
              <div className="dgii-filter-bar">
                <div className="dgii-search-box">
                  <Search size={15} />
                  <input
                    type="text"
                    placeholder="Buscar e-NCF o RNC..."
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                  />
                </div>
                <div className="dgii-filter-pills">
                  <button type="button" className={statusFilter === 'all' ? 'active' : ''} onClick={() => setStatusFilter('all')}>Todos</button>
                  <button type="button" className={statusFilter === 'approved' ? 'active' : ''} onClick={() => setStatusFilter('approved')}>Aprobados</button>
                  <button type="button" className={statusFilter === 'rejected' ? 'active' : ''} onClick={() => setStatusFilter('rejected')}>Rechazados</button>
                  <button type="button" className={statusFilter === 'pending' ? 'active' : ''} onClick={() => setStatusFilter('pending')}>Pendientes</button>
                  <button type="button" className={statusFilter === 'not_found' ? 'active' : ''} onClick={() => setStatusFilter('not_found')}>No encontrados</button>
                </div>
              </div>
              <div className="dgii-certification-table-wrap">
                <table className="dgii-certification-table compact">
                  <thead>
                    <tr>
                      <th>e-NCF</th>
                      <th>RNC emisor</th>
                      <th>RNC comprador</th>
                      <th>Monto</th>
                      <th>Decisión Excel</th>
                      <th>DGII</th>
                      <th>Fecha aprobación</th>
                      <th>Coincidencia</th>
                      <th>Detalle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item) => (
                      <tr key={item.id} className={String(item.id) === String(selectedItemId) ? 'selected' : ''}>
                        <td data-label="e-NCF">{item.encf}</td>
                        <td data-label="RNC emisor">{item.issuer_rnc}</td>
                        <td data-label="RNC comprador">{item.buyer_rnc || 'No disponible'}</td>
                        <td data-label="Monto">{item.total_amount || 'No disponible'}</td>
                        <td data-label="Decisión Excel">{statusBadge(statusMeta(item.source_approval_status))}</td>
                        <td data-label="DGII">{statusBadge(submissionMeta(item.submission_status))}</td>
                        <td data-label="Fecha aprobación">{formatDate(item.commercial_approval_at, true)}</td>
                        <td data-label="Coincidencia">{statusBadge(matchMeta(item.match_status))}</td>
                        <td data-label="Detalle">
                          <button
                            type="button"
                            className="dgii-wizard-mini-action secondary"
                            onClick={() => setSelectedItemId(item.id)}
                          >
                            Ver detalle
                          </button>
                        </td>
                      </tr>
                    ))}
                    {filteredItems.length === 0 && (
                      <tr>
                        <td colSpan={9} className="dgii-table-empty-row">Sin aprobaciones para este filtro.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {selectedItem && (
                <div className="dgii-tests-detail">
                  <div className="dgii-wizard-card-header">
                    <div>
                      <h2>{selectedItem.encf}</h2>
                      <p>Decisión: {selectedItem.source_approval_status_label} · DGII: {selectedItem.submission_status_label}</p>
                    </div>
                    <button type="button" className="dgii-wizard-mini-action secondary" onClick={() => setSelectedItemId(null)}>
                      Cerrar
                    </button>
                  </div>
                  <div className="dgii-tests-detail-grid">
                    <div><span>Documento local</span><strong>{selectedItem.matched_document_type || 'No encontrado'}</strong></div>
                    <div><span>ID local</span><strong>{selectedItem.matched_document_id || 'No disponible'}</strong></div>
                    <div><span>Estado match</span><strong>{selectedItem.match_status_label}</strong></div>
                    <div><span>Receptor aprobación</span><strong>{selectedItem.approval_receiver_rnc || selectedItem.buyer_rnc || 'No disponible'}</strong></div>
                    <div><span>Fecha emisión</span><strong>{formatDate(selectedItem.issue_date)}</strong></div>
                    <div><span>Versión</span><strong>{selectedItem.version || 'No disponible'}</strong></div>
                    <div><span>Fila</span><strong>{selectedItem.source_row}</strong></div>
                    <div><span>TrackID</span><strong>{selectedItem.dgii_track_id || 'No disponible'}</strong></div>
                    <div><span>Respuesta DGII</span><strong>{selectedItem.dgii_response_code || 'No disponible'}</strong></div>
                  </div>
                  <p className="dgii-tests-full-message">
                    {selectedItem.submission_error || selectedItem.dgii_response_message || selectedItem.rejection_reason || selectedItem.match_observations || 'Sin observaciones.'}
                  </p>
                </div>
              )}
            </article>
          </>
        )}
      </section>
    </div>
  );
}
