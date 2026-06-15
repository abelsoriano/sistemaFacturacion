import React from 'react';
import { Badge, Tag } from 'antd';

const FISCAL_STATUS_META = {
  draft: { color: 'default', text: 'Borrador', badge: 'default' },
  xml_generated: { color: 'blue', text: 'XML generado', badge: 'processing' },
  signed: { color: 'geekblue', text: 'Firmado', badge: 'processing' },
  submitted: { color: 'cyan', text: 'Enviado', badge: 'processing' },
  accepted: { color: 'green', text: 'Aceptado', badge: 'success' },
  rejected: { color: 'red', text: 'Rechazado', badge: 'error' },
};

const JOB_STATUS_META = {
  idle: { color: 'default', text: 'Inactivo', badge: 'default' },
  queued: { color: 'processing', text: 'En cola', badge: 'processing' },
  running: { color: 'blue', text: 'Ejecutando', badge: 'processing' },
  retrying: { color: 'gold', text: 'Reintentando', badge: 'warning' },
  failed: { color: 'volcano', text: 'Fallido', badge: 'error' },
};

const LEGACY_STATUS_META = {
  ...FISCAL_STATUS_META,
  queued: JOB_STATUS_META.queued,
  pending: { color: 'gold', text: 'Pendiente DGII', badge: 'warning' },
  processing: { color: 'purple', text: 'Procesando', badge: 'processing' },
  error: JOB_STATUS_META.failed,
  cancelled: { color: 'default', text: 'Anulado', badge: 'default' },
};

export const ACTIVE_STATUSES = new Set(['submitted']);
export const ACTIVE_JOB_STATUSES = new Set(['queued', 'running', 'retrying']);
export const TERMINAL_STATUSES = new Set(['accepted', 'rejected']);

export function getStatusMeta(status) {
  return LEGACY_STATUS_META[status] || { color: 'default', text: status || 'N/D', badge: 'default' };
}

export function getFiscalStatusMeta(status) {
  return FISCAL_STATUS_META[status] || getStatusMeta(status);
}

export function getJobStatusMeta(status) {
  return JOB_STATUS_META[status] || { color: 'default', text: status || 'N/D', badge: 'default' };
}

function StatusTag({ meta, active }) {
  return (
    <Badge status={meta.badge}>
      <Tag color={meta.color} className={active ? 'ecf-pulse-tag' : undefined}>
        {meta.text}
      </Tag>
    </Badge>
  );
}

export function EcfFiscalStatusBadge({ status, pulse = false }) {
  const meta = getFiscalStatusMeta(status);
  return <StatusTag meta={meta} active={pulse && ACTIVE_STATUSES.has(status)} />;
}

export function EcfJobStatusBadge({ status, pulse = false }) {
  const meta = getJobStatusMeta(status);
  return <StatusTag meta={meta} active={pulse && ACTIVE_JOB_STATUSES.has(status)} />;
}

function EcfStatusBadge({ status, pulse = false, type = 'legacy' }) {
  if (type === 'fiscal') return <EcfFiscalStatusBadge status={status} pulse={pulse} />;
  if (type === 'job') return <EcfJobStatusBadge status={status} pulse={pulse} />;
  const meta = getStatusMeta(status);
  const isActive = pulse && (ACTIVE_STATUSES.has(status) || ACTIVE_JOB_STATUSES.has(status));

  return <StatusTag meta={meta} active={isActive} />;
}

export default EcfStatusBadge;
