import React from 'react';
import { Button, Card, Col, Descriptions, Drawer, Row, Space, Spin, Tabs, Typography } from 'antd';
import {
  CloudUploadOutlined,
  DownloadOutlined,
  ReloadOutlined,
  RetweetOutlined,
} from '@ant-design/icons';
import moment from 'moment';
import EcfEventTimeline from './EcfEventTimeline';
import { ACTIVE_JOB_STATUSES, EcfFiscalStatusBadge, EcfJobStatusBadge, TERMINAL_STATUSES } from './EcfStatusBadge';
import { downloadFiscalArtifact } from '../../services/ecf/ecfApi';

const XmlPreview = ({ title, available, onDownload }) => (
  <Card
    title={title}
    bordered={false}
    className="ecf-panel-card"
    extra={
      <Button
        icon={<DownloadOutlined />}
        disabled={!available}
        onClick={onDownload}
      >
        Descargar
      </Button>
    }
  >
    {available ? (
      <Typography.Text type="secondary">Disponible para descarga segura de auditoria.</Typography.Text>
    ) : (
      <Typography.Text type="secondary">No disponible</Typography.Text>
    )}
  </Card>
);

function EcfDocumentDetail({
  open,
  document,
  loading,
  onClose,
  onRefresh,
  actions,
  actionLoading,
}) {
  const fiscalStatus = document?.fiscal_status || document?.status;
  const jobStatus = document?.job_status || 'idle';
  const isTerminal = document?.is_terminal_fiscal ?? TERMINAL_STATUSES.has(fiscalStatus);
  const hasTrackId = Boolean(document?.track_id);
  const canRetry = document?.can_retry ?? (document && !hasTrackId && !isTerminal);
  const canCheckStatus = document?.can_check_status ?? (hasTrackId && !isTerminal);
  const canProcess = document && !isTerminal && !ACTIVE_JOB_STATUSES.has(jobStatus);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={980}
      title={
        <div className="ecf-drawer-title">
          <span>{document?.encf || 'Documento e-CF'}</span>
          {fiscalStatus && <EcfFiscalStatusBadge status={fiscalStatus} pulse />}
          {document && <EcfJobStatusBadge status={jobStatus} pulse />}
        </div>
      }
      extra={
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading}>
            Actualizar
          </Button>
          <Button
            icon={<ReloadOutlined />}
            disabled={!canCheckStatus}
            loading={actionLoading.status}
            onClick={actions.checkStatus}
          >
            Consultar DGII
          </Button>
          <Button
            icon={<RetweetOutlined />}
            disabled={!canRetry}
            loading={actionLoading.retry}
            onClick={actions.retry}
          >
            Reenviar
          </Button>
          <Button
            type="primary"
            icon={<CloudUploadOutlined />}
            disabled={!canProcess}
            loading={actionLoading.process}
            onClick={actions.process}
          >
            Procesar
          </Button>
        </Space>
      }
    >
      {loading && !document ? (
        <div className="ecf-detail-loading"><Spin /></div>
      ) : (
        <Tabs
          defaultActiveKey="summary"
          items={[
            {
              key: 'summary',
              label: 'Resumen',
              children: (
                <Row gutter={[16, 16]}>
                  <Col span={24}>
                    <Card bordered={false} className="ecf-panel-card">
                      <Descriptions column={{ xs: 1, md: 2 }} size="middle">
                        <Descriptions.Item label="Factura">{document?.invoice_number || 'N/D'}</Descriptions.Item>
                        <Descriptions.Item label="Tipo">e-CF {document?.ecf_type || 'N/D'}</Descriptions.Item>
                        <Descriptions.Item label="Estado fiscal">
                          <EcfFiscalStatusBadge status={fiscalStatus} />
                        </Descriptions.Item>
                        <Descriptions.Item label="Proceso">
                          <EcfJobStatusBadge status={jobStatus} />
                        </Descriptions.Item>
                        <Descriptions.Item label="TrackID">
                          {document?.track_id ? <Typography.Text copyable>{document.track_id}</Typography.Text> : 'N/D'}
                        </Descriptions.Item>
                        <Descriptions.Item label="Emisor">{document?.issuer_name || 'N/D'}</Descriptions.Item>
                        <Descriptions.Item label="Intentos envío">{document?.submission_attempts || 0}</Descriptions.Item>
                        <Descriptions.Item label="Consultas estado">{document?.status_check_attempts || 0}</Descriptions.Item>
                        <Descriptions.Item label="Último envío">
                          {document?.last_submitted_at ? moment(document.last_submitted_at).format('DD/MM/YYYY HH:mm') : 'N/D'}
                        </Descriptions.Item>
                        <Descriptions.Item label="Última consulta">
                          {document?.last_status_checked_at ? moment(document.last_status_checked_at).format('DD/MM/YYYY HH:mm') : 'N/D'}
                        </Descriptions.Item>
                        <Descriptions.Item label="Aceptado">
                          {document?.accepted_at ? moment(document.accepted_at).format('DD/MM/YYYY HH:mm') : 'N/D'}
                        </Descriptions.Item>
                        <Descriptions.Item label="Próximo retry">
                          {document?.next_retry_at ? moment(document.next_retry_at).format('DD/MM/YYYY HH:mm') : 'N/D'}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>
                  {(document?.last_error || document?.rejection_reason) && (
                    <Col span={24}>
                      <Card title="Error fiscal" bordered={false} className="ecf-error-card">
                        <Typography.Paragraph>{document.last_error || document.rejection_reason}</Typography.Paragraph>
                      </Card>
                    </Col>
                  )}
                </Row>
              ),
            },
            {
              key: 'events',
              label: 'Timeline',
              children: <EcfEventTimeline events={document?.events || []} />,
            },
            {
              key: 'xml',
              label: 'XML',
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <XmlPreview
                      title="XML original"
                      available={document?.xml_available}
                      onDownload={() => downloadFiscalArtifact(document.id, 'xml', `${document?.encf || 'ecf'}-original.xml`)}
                    />
                  </Col>
                  <Col xs={24} lg={12}>
                    <XmlPreview
                      title="XML firmado"
                      available={document?.signed_xml_available}
                      onDownload={() => downloadFiscalArtifact(document.id, 'signed-xml', `${document?.encf || 'ecf'}-firmado.xml`)}
                    />
                  </Col>
                </Row>
              ),
            },
            {
              key: 'dgii',
              label: 'DGII',
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <XmlPreview
                      title="Request SOAP"
                      available={document?.dgii_request_available}
                      onDownload={() => downloadFiscalArtifact(document.id, 'dgii-request', `${document?.encf || 'ecf'}-dgii-request.xml`)}
                    />
                  </Col>
                  <Col xs={24} lg={12}>
                    <XmlPreview
                      title="Response SOAP"
                      available={document?.dgii_response_available}
                      onDownload={() => downloadFiscalArtifact(document.id, 'dgii-response', `${document?.encf || 'ecf'}-dgii-response.xml`)}
                    />
                  </Col>
                  <Col span={24}>
                    <Card title="Respuesta normalizada" bordered={false} className="ecf-panel-card">
                      <pre className="ecf-json-block">{JSON.stringify(document?.dgii_response || {}, null, 2)}</pre>
                    </Card>
                  </Col>
                </Row>
              ),
            },
          ]}
        />
      )}
    </Drawer>
  );
}

export default EcfDocumentDetail;
