import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Download,
  ExternalLink,
  FileCheck2,
  FileSignature,
  FileUp,
  Info,
  ListChecks,
  ShieldCheck,
} from 'lucide-react';

import api from '../services/api';
import notify from '../utils/notify';
import '../css/DGIICertificationWizard.css';

const MAX_XML_BYTES = 2 * 1024 * 1024;
const STORAGE_KEY = 'dgii_certification_wizard_state';
const MAX_EXCEL_BYTES = 5 * 1024 * 1024;

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

const certificateStatusMeta = {
  missing: { label: 'Faltante', tone: 'danger' },
  active: { label: 'Activo', tone: 'success' },
  expiring_soon: { label: 'Por vencer', tone: 'warning' },
  expired: { label: 'Vencido', tone: 'danger' },
  invalid: { label: 'Inválido', tone: 'danger' },
};

const rncMatchMeta = {
  matched: { label: 'Coincide', tone: 'success' },
  mismatch: { label: 'No coincide', tone: 'danger' },
  not_found: { label: 'No encontrado', tone: 'warning' },
  unknown: { label: 'Desconocido', tone: 'warning' },
};

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

export default function DGIICertificationWizard() {
  const [company, setCompany] = useState(null);
  const [issuers, setIssuers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [selectedIssuerId, setSelectedIssuerId] = useState('');
  const [loading, setLoading] = useState(true);
  const [signing, setSigning] = useState(false);
  const [importingSet, setImportingSet] = useState(false);
  const [generatingXml, setGeneratingXml] = useState('');
  const [error, setError] = useState('');
  const [activeSection, setActiveSection] = useState('certificate');
  const [xmlFile, setXmlFile] = useState(null);
  const [xmlContent, setXmlContent] = useState('');
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
      const plansResponse = await api.get('/ecf/certification-plans/').catch(() => ({ data: [] }));
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
      setXmlContent(content);
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
      setActiveSection('tests');
      notify.success('Set DGII importado', `${response.data.total_items || 0} escenarios detectados.`);
    } catch (err) {
      notify.error('No se pudo importar', err.response?.data?.detail || 'Revise el formato del Excel DGII.');
    } finally {
      setImportingSet(false);
      event.target.value = '';
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

  const checklist = [
    {
      label: 'Certificado cargado',
      done: Boolean(activeCertificate || selectedIssuer?.certificate_status !== 'missing'),
    },
    {
      label: 'Certificado válido',
      done: selectedIssuer?.certificate_status === 'active' || activeCertificate?.status === 'active',
    },
    {
      label: 'XML generado',
      done: ['xml_generated', 'xml_signed', 'sent_to_dgii', 'approved'].includes(applicationState),
    },
    {
      label: 'XML firmado',
      done: ['xml_signed', 'sent_to_dgii', 'approved'].includes(applicationState),
    },
    {
      label: 'XML enviado a DGII',
      done: ['sent_to_dgii', 'approved'].includes(applicationState),
    },
    {
      label: 'Postulación aprobada',
      done: applicationState === 'approved',
    },
    {
      label: 'Ambiente de certificación habilitado',
      done: applicationState === 'approved',
    },
  ];

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

  if (loading) {
    return (
      <section className="dgii-wizard-page">
        <div className="dgii-wizard-loading">Cargando certificación DGII...</div>
      </section>
    );
  }

  return (
    <section className="dgii-wizard-page">
      <header className="dgii-wizard-header">
        <div>
          <p className="dgii-wizard-eyebrow">Empresa / Certificación DGII</p>
          <h1>Certificación DGII</h1>
          <p>Acompaña la postulación e-CF sin afectar la emisión fiscal normal.</p>
        </div>
        <button type="button" className="dgii-wizard-secondary" onClick={loadData}>
          Actualizar estado
        </button>
      </header>

      <nav className="dgii-wizard-tabs" aria-label="Secciones certificacion DGII">
        <button
          type="button"
          className={activeSection === 'certificate' ? 'active' : ''}
          onClick={() => setActiveSection('certificate')}
        >
          Certificado
        </button>
        <button
          type="button"
          className={activeSection === 'application' ? 'active' : ''}
          onClick={() => setActiveSection('application')}
        >
          Postulación
        </button>
        <button
          type="button"
          className={activeSection === 'tests' ? 'active' : ''}
          onClick={() => setActiveSection('tests')}
        >
          Pruebas e-CF
        </button>
      </nav>

      {error && (
        <div className="dgii-wizard-alert danger">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {activeSection === 'certificate' && (
      <div className="dgii-wizard-grid">
        <article className="dgii-wizard-card span-2">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Estado del certificado</h2>
              <p>{company?.name || 'Empresa activa'} · emisor fiscal DGII</p>
            </div>
            <ShieldCheck size={24} />
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

              <div className="dgii-wizard-status-grid">
                <div>
                  <span>Estado técnico</span>
                  {statusBadge(certificateStatusMeta[activeCertificate?.status || selectedIssuer?.certificate_status])}
                </div>
                <div>
                  <span>RNC detectado</span>
                  <strong>{activeCertificate?.rnc_detected || selectedIssuer?.certificate_rnc_detected || 'No disponible'}</strong>
                </div>
                <div>
                  <span>Coincidencia RNC</span>
                  {statusBadge(rncMatchMeta[activeCertificate?.rnc_match_status || selectedIssuer?.certificate_rnc_match_status])}
                </div>
                <div>
                  <span>Válido hasta</span>
                  <strong>{formatDate(activeCertificate?.not_valid_after || selectedIssuer?.certificate_not_valid_after)}</strong>
                </div>
              </div>

              <div className="dgii-wizard-certificate-box">
                <BadgeCheck size={20} />
                <div>
                  <strong>{activeCertificate ? 'Certificado activo versionado' : 'Metadata legacy del emisor'}</strong>
                  <p>Fingerprint: {compact(activeCertificate?.fingerprint || selectedIssuer?.certificate_fingerprint)}</p>
                  <p>Este certificado será usado para futuras firmas de postulación.</p>
                </div>
              </div>

              {(activeCertificate?.rnc_match_status || selectedIssuer?.certificate_rnc_match_status) === 'mismatch' && (
                <div className="dgii-wizard-alert danger">
                  <AlertTriangle size={18} />
                  <span>El RNC detectado en el certificado no coincide con el RNC del emisor.</span>
                </div>
              )}
            </>
          )}
        </article>

        <article className="dgii-wizard-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Estado de postulación</h2>
              <p>Control visual local</p>
            </div>
            <FileCheck2 size={24} />
          </div>
          <div className="dgii-wizard-steps">
            {applicationStates.map((state, index) => {
              const currentIndex = applicationStates.findIndex((item) => item.value === applicationState);
              const done = index <= currentIndex;
              return (
                <button
                  key={state.value}
                  type="button"
                  className={`dgii-wizard-step ${done ? 'done' : ''} ${state.value === applicationState ? 'current' : ''}`}
                  onClick={() => updateApplicationState(state.value)}
                >
                  <span>{done ? <CheckCircle2 size={16} /> : index + 1}</span>
                  {state.label}
                </button>
              );
            })}
          </div>
        </article>

        <article className="dgii-wizard-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Asistente guiado</h2>
              <p>Siguiente acción recomendada</p>
            </div>
            <Info size={24} />
          </div>
          <div className="dgii-wizard-recommendation">{recommendation}</div>
        </article>
      </div>
      )}

      {activeSection === 'application' && (
      <div className="dgii-wizard-grid">
        <article className="dgii-wizard-card span-2">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>XML de postulación</h2>
              <p>Archivo generado desde el portal de certificación DGII</p>
            </div>
            <FileUp size={24} />
          </div>

          <div className="dgii-wizard-upload">
            <label className="dgii-wizard-file">
              <input type="file" accept=".xml,application/xml,text/xml" onChange={handleXmlChange} />
              <FileUp size={20} />
              Seleccionar XML
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
          </div>

          {xmlInfo ? (
            <div className="dgii-wizard-xml-info">
              <div>
                <span>Archivo</span>
                <strong>{xmlInfo.filename}</strong>
              </div>
              <div>
                <span>Raíz XML</span>
                <strong>{xmlInfo.rootName}</strong>
              </div>
              <div>
                <span>Tamaño</span>
                <strong>{Math.ceil(xmlInfo.size / 1024)} KB</strong>
              </div>
              <div>
                <span>Cargado</span>
                <strong>{formatDate(xmlInfo.uploadedAt, true)}</strong>
              </div>
            </div>
          ) : (
            <div className="dgii-wizard-empty">Seleccione el XML descargado del portal DGII para iniciar la firma.</div>
          )}

          <div className="dgii-wizard-actions">
            <button
              type="button"
              className="dgii-wizard-secondary"
              disabled={!xmlContent}
              onClick={() => downloadTextFile(xmlInfo?.filename || 'postulacion-dgii.xml', xmlContent)}
            >
              <Download size={18} />
              Descargar XML original
            </button>
            <button
              type="button"
              className="dgii-wizard-primary"
              disabled={!signedXml}
              onClick={() => downloadTextFile(signedFilename, signedXml)}
            >
              <Download size={18} />
              Descargar XML firmado
            </button>
          </div>
        </article>

        <article className="dgii-wizard-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Checklist DGII</h2>
              <p>Seguimiento visual</p>
            </div>
            <CheckCircle2 size={24} />
          </div>
          <div className="dgii-wizard-checklist">
            {checklist.map((item) => (
              <div key={item.label} className={item.done ? 'done' : ''}>
                <span>{item.done ? '✓' : '□'}</span>
                {item.label}
              </div>
            ))}
          </div>
        </article>

        <article className="dgii-wizard-card">
          <div className="dgii-wizard-card-header">
            <div>
              <h2>Enlaces útiles</h2>
              <p>Recursos externos</p>
            </div>
            <ExternalLink size={24} />
          </div>
          <div className="dgii-wizard-links">
            <a href="https://ecf.dgii.gov.do/certecf/portalcertificacion" target="_blank" rel="noreferrer">
              Portal certificación DGII
            </a>
            <a href="https://ra.viafirma.do" target="_blank" rel="noreferrer">
              Solicitud certificado Viafirma
            </a>
            <a href={process.env.REACT_APP_DGII_DOCS_URL || 'https://dgii.gov.do'} target="_blank" rel="noreferrer">
              Documentación DGII
            </a>
          </div>
        </article>
      </div>
      )}

      {activeSection === 'tests' && (
        <DGIICertificationTestsSection
          importingSet={importingSet}
          generatingXml={generatingXml}
          latestPlan={latestPlan}
          plans={plans}
          onImportSet={handleImportSet}
          onGenerateItemXml={handleGenerateItemXml}
          onGenerateGroupXml={handleGenerateGroupXml}
          onDownloadGeneratedXml={handleDownloadGeneratedXml}
        />
      )}
    </section>
  );
}

function DGIICertificationTestsSection({
  importingSet,
  generatingXml,
  latestPlan,
  plans,
  onImportSet,
  onGenerateItemXml,
  onGenerateGroupXml,
  onDownloadGeneratedXml,
}) {
  const groupCounts = latestPlan?.group_counts || {};
  const statusCounts = (latestPlan?.items || []).reduce((acc, item) => {
    acc[item.status] = (acc[item.status] || 0) + 1;
    return acc;
  }, {});

  const groups = [
    { id: '1', title: 'Grupo 1', detail: '31, 32 >= 250,000, 41, 43, 44, 45, 46, 47' },
    { id: '2', title: 'Grupo 2', detail: '33, 34' },
    { id: '3', title: 'Grupo 3', detail: 'RFCE / Resúmenes de consumo' },
    { id: '4', title: 'Grupo 4', detail: '32 < 250,000' },
  ];

  return (
    <div className="dgii-wizard-grid">
      <article className="dgii-wizard-card span-2">
        <div className="dgii-wizard-card-header">
          <div>
            <h2>Paso 2 DGII — Pruebas de Datos e-CF</h2>
            <p>Importa el Excel entregado por DGII y genera el plan de certificación.</p>
          </div>
          <ListChecks size={24} />
        </div>

        <div className="dgii-wizard-upload">
          <label className="dgii-wizard-file">
            <input type="file" accept=".xlsx,.xls" onChange={onImportSet} disabled={importingSet} />
            <FileUp size={20} />
            {importingSet ? 'Importando...' : 'Importar Set DGII'}
          </label>
        </div>

        {latestPlan ? (
          <>
            <div className="dgii-wizard-xml-info dgii-wizard-plan-info">
              <div>
                <span>Archivo</span>
                <strong>{latestPlan.source_filename}</strong>
              </div>
              <div>
                <span>Escenarios</span>
                <strong>{latestPlan.total_items}</strong>
              </div>
              <div>
                <span>Importado</span>
                <strong>{formatDate(latestPlan.imported_at, true)}</strong>
              </div>
              <div>
                <span>Estado inicial</span>
                <strong>{statusCounts.pending || 0} pendientes</strong>
              </div>
            </div>

            <div className="dgii-certification-groups">
              {groups.map((group) => (
                <div key={group.id}>
                  <strong>{group.title}</strong>
                  <span>{group.detail}</span>
                  <b>{groupCounts[group.id] || 0}</b>
                  <button
                    type="button"
                    className="dgii-wizard-mini-action"
                    disabled={!latestPlan || generatingXml === `group-${group.id}`}
                    onClick={() => onGenerateGroupXml(latestPlan.id, group.id)}
                  >
                    {generatingXml === `group-${group.id}` ? 'Preparando...' : 'Preparar grupo'}
                  </button>
                </div>
              ))}
            </div>

            <div className="dgii-certification-table-wrap">
              <table className="dgii-certification-table">
                <thead>
                  <tr>
                    <th>Grupo</th>
                    <th>Tipo</th>
                    <th>e-NCF</th>
                    <th>Monto</th>
                    <th>Receptor</th>
                    <th>Origen</th>
                    <th>Estado</th>
                    <th>Escenario</th>
                  </tr>
                </thead>
                <tbody>
                  {(latestPlan.items || []).map((item) => (
                    <tr key={item.id}>
                      <td data-label="Grupo">{item.dgii_group}</td>
                      <td data-label="Tipo">{item.ecf_type} · {item.ecf_type_label}</td>
                      <td data-label="e-NCF">{item.encf || 'No detectado'}</td>
                      <td data-label="Monto">{item.amount || 'No disponible'}</td>
                      <td data-label="Receptor">{item.receiver_name || item.receiver_rnc || 'No disponible'}</td>
                      <td data-label="Origen">{item.source_sheet} · fila {item.source_row}</td>
                      <td data-label="Estado">{statusBadge({ label: item.status_label || 'Pendiente', tone: 'neutral' })}</td>
                      <td data-label="Escenario">
                        <div className="dgii-certification-actions">
                          {item.status === 'generation_error' ? (
                            <span title={item.generation_error}>{item.generation_error || 'Error generación'}</span>
                          ) : (
                            <button
                              type="button"
                              className="dgii-wizard-mini-action"
                              disabled={generatingXml === `item-${item.id}`}
                              onClick={() => onGenerateItemXml(latestPlan.id, item.id)}
                            >
                              {generatingXml === `item-${item.id}` ? 'Preparando...' : 'Preparar'}
                            </button>
                          )}
                          {item.generated_xml_path && (
                            <button
                              type="button"
                              className="dgii-wizard-mini-action secondary"
                              onClick={() => onDownloadGeneratedXml(latestPlan.id, item)}
                            >
                              Descargar
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="dgii-wizard-empty">Aún no hay plan de certificación importado para esta empresa.</div>
        )}
      </article>

      <article className="dgii-wizard-card">
        <div className="dgii-wizard-card-header">
          <div>
            <h2>Historial de planes</h2>
            <p>Importaciones recientes</p>
          </div>
        </div>
        <div className="dgii-certification-history">
          {plans.length === 0 ? (
            <span>No hay importaciones.</span>
          ) : plans.map((plan) => (
            <div key={plan.id}>
              <strong>{plan.source_filename}</strong>
              <span>{plan.total_items} escenarios · {formatDate(plan.imported_at, true)}</span>
            </div>
          ))}
        </div>
      </article>

      <article className="dgii-wizard-card">
        <div className="dgii-wizard-card-header">
          <div>
            <h2>Alcance de esta fase</h2>
            <p>Plan visual y auditoría</p>
          </div>
        </div>
        <div className="dgii-wizard-recommendation">
          Esta fase no genera XML, no firma escenarios, no consume secuencias y no envía a DGII.
          Todos los casos importados inician como pendientes.
        </div>
      </article>
    </div>
  );
}
