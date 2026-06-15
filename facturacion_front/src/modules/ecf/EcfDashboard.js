import React, { useState } from 'react';
import { Alert, Button, Card, Statistic, Tabs } from 'antd';
import { HomeOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import E34CreditNoteFilters from '../../components/ecf/E34CreditNoteFilters';
import E34CreditNoteTable from '../../components/ecf/E34CreditNoteTable';
import EcfAsyncMonitor from '../../components/ecf/EcfAsyncMonitor';
import EcfDocumentDetail from '../../components/ecf/EcfDocumentDetail';
import EcfDocumentTable from '../../components/ecf/EcfDocumentTable';
import EcfFilters from '../../components/ecf/EcfFilters';
import EcfMetricCards from '../../components/ecf/EcfMetricCards';
import { useE34CreditNotes } from '../../hooks/ecf/useE34CreditNotes';
import { useEcfDocument } from '../../hooks/ecf/useEcfDocument';
import { useEcfDocuments } from '../../hooks/ecf/useEcfDocuments';
import './ecf.css';

function EcfDashboard() {
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState(null);
  const {
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
  } = useEcfDocuments({ poll: true });
  const e34 = useE34CreditNotes({ poll: true });

  const detail = useEcfDocument(selectedId, { poll: Boolean(selectedId) });

  const openDocument = (record) => setSelectedId(record.id);
  const openE34Document = (record) => setSelectedId(record.electronic_document_id);
  const rejectedDocuments = documents.filter((item) => (item.fiscal_status || item.status) === 'rejected');
  const technicalErrorDocuments = documents.filter((item) => item.job_status === 'failed' || item.last_error);

  return (
    <div className="ecf-shell">
      <div className="ecf-header">
        <div>
          <h1>Operación e-CF</h1>
          <p>Monitoreo fiscal, procesamiento DGII y auditoría electrónica.</p>
        </div>
        <div className="ecf-header-actions">
          <Button icon={<ReloadOutlined />} onClick={() => refresh()} loading={loading}>
            Actualizar
          </Button>
          <Button type="primary" icon={<HomeOutlined />} onClick={() => navigate('/home')}>
            Inicio
          </Button>
        </div>
      </div>

      {error && <Alert type="error" showIcon message={error} className="ecf-alert" />}

      <EcfMetricCards monitor={monitor} />

      <Card bordered={false} className="ecf-main-card">
        <Tabs
          defaultActiveKey="documents"
          items={[
            {
              key: 'documents',
              label: 'Documentos',
              children: (
                <>
                  <EcfFilters
                    filters={filters}
                    onChange={(nextFilters) => {
                      setPage(1);
                      setFilters(nextFilters);
                    }}
                    onRefresh={() => refresh()}
                    loading={loading}
                  />
                  <EcfDocumentTable
                    documents={documents}
                    loading={loading}
                    total={total}
                    page={page}
                    pageSize={pageSize}
                    onPageChange={(nextPage, nextSize) => {
                      setPage(nextPage);
                      setPageSize(nextSize);
                    }}
                    onOpen={openDocument}
                    actions={actions}
                    actionLoading={actionLoading}
                  />
                </>
              ),
            },
            {
              key: 'e34-notes',
              label: 'Notas E34',
              children: (
                <>
                  {e34.error && <Alert type="error" showIcon message={e34.error} className="ecf-alert" />}
                  <div className="e34-summary-grid">
                    <Card bordered={false} className="ecf-metric-card"><Statistic title="Aceptadas" value={e34.summary?.accepted || 0} /></Card>
                    <Card bordered={false} className="ecf-metric-card"><Statistic title="Pendientes" value={e34.summary?.pending || 0} /></Card>
                    <Card bordered={false} className="ecf-metric-card"><Statistic title="Rechazadas" value={e34.summary?.rejected || 0} /></Card>
                    <Card bordered={false} className="ecf-metric-card"><Statistic title="Revisión" value={e34.summary?.requires_manual_review || 0} /></Card>
                    <Card bordered={false} className="ecf-metric-card"><Statistic title="Inventario pendiente" value={e34.summary?.inventory_restored_pending || 0} /></Card>
                    <Card bordered={false} className="ecf-metric-card"><Statistic title="Inventario compensado" value={e34.summary?.inventory_compensated || 0} /></Card>
                  </div>
                  <E34CreditNoteFilters
                    filters={e34.filters}
                    onChange={(nextFilters) => {
                      e34.setPage(1);
                      e34.setFilters(nextFilters);
                    }}
                    onRefresh={() => e34.refresh()}
                    loading={e34.loading}
                  />
                  <E34CreditNoteTable
                    notes={e34.notes}
                    loading={e34.loading}
                    total={e34.total}
                    page={e34.page}
                    pageSize={e34.pageSize}
                    onPageChange={(nextPage, nextSize) => {
                      e34.setPage(nextPage);
                      e34.setPageSize(nextSize);
                    }}
                    onOpenDocument={openE34Document}
                    actions={e34.actions}
                    actionLoading={e34.actionLoading}
                  />
                </>
              ),
            },
            {
              key: 'monitor',
              label: 'Monitor async',
              children: <EcfAsyncMonitor monitor={monitor} />,
            },
            {
              key: 'errors',
              label: 'Rechazos DGII',
              children: (
                <EcfDocumentTable
                  documents={rejectedDocuments}
                  loading={loading}
                  total={rejectedDocuments.length}
                  page={1}
                  pageSize={10}
                  onPageChange={() => {}}
                  onOpen={openDocument}
                  actions={actions}
                  actionLoading={actionLoading}
                />
              ),
            },
            {
              key: 'technical-errors',
              label: 'Fallos técnicos',
              children: (
                <EcfDocumentTable
                  documents={technicalErrorDocuments}
                  loading={loading}
                  total={technicalErrorDocuments.length}
                  page={1}
                  pageSize={10}
                  onPageChange={() => {}}
                  onOpen={openDocument}
                  actions={actions}
                  actionLoading={actionLoading}
                />
              ),
            },
            {
              key: 'retries',
              label: 'Retries pendientes',
              children: (
                <EcfDocumentTable
                  documents={documents.filter((item) => item.next_retry_at)}
                  loading={loading}
                  total={documents.filter((item) => item.next_retry_at).length}
                  page={1}
                  pageSize={10}
                  onPageChange={() => {}}
                  onOpen={openDocument}
                  actions={actions}
                  actionLoading={actionLoading}
                />
              ),
            },
          ]}
        />
      </Card>

      <EcfDocumentDetail
        open={Boolean(selectedId)}
        document={detail.document}
        loading={detail.loading}
        onClose={() => setSelectedId(null)}
        onRefresh={() => detail.refresh()}
        actions={detail.actions}
        actionLoading={detail.actionLoading}
      />
    </div>
  );
}

export default EcfDashboard;
