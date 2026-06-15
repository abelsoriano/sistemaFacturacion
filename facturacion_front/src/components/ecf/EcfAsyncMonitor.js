import React from 'react';
import { Card, Col, Empty, Row, Statistic, Table, Tag } from 'antd';
import moment from 'moment';
import { EcfFiscalStatusBadge, EcfJobStatusBadge } from './EcfStatusBadge';

function EcfAsyncMonitor({ monitor }) {
  const errors = monitor?.recent_errors || [];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={8}>
        <Card title="Monitor async" bordered={false} className="ecf-panel-card">
          <div className="ecf-monitor-grid">
            <Statistic title="Retries pendientes" value={monitor?.retry_pending || 0} />
            <Statistic title="Fallos técnicos" value={monitor?.technical_failed || 0} />
            <Statistic title="Intentos envío" value={monitor?.submission_attempts || 0} />
            <Statistic title="Consultas estado" value={monitor?.status_check_attempts || 0} />
          </div>
        </Card>
      </Col>
      <Col xs={24} lg={16}>
        <Card title="Estados fiscales" bordered={false} className="ecf-panel-card">
          <div className="ecf-status-strip">
            {(monitor?.by_fiscal_status || monitor?.by_status || []).map((item) => (
              <div className="ecf-status-chip" key={item.fiscal_status || item.status}>
                <EcfFiscalStatusBadge status={item.fiscal_status || item.status} />
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
          <div className="ecf-status-strip">
            {(monitor?.by_job_status || []).map((item) => (
              <div className="ecf-status-chip" key={item.job_status}>
                <EcfJobStatusBadge status={item.job_status} />
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </Card>
      </Col>
      <Col span={24}>
        <Card title="Errores recientes" bordered={false} className="ecf-panel-card">
          {errors.length ? (
            <Table
              rowKey="id"
              size="small"
              dataSource={errors}
              pagination={false}
              columns={[
                { title: 'e-NCF', dataIndex: 'encf', width: 150 },
                { title: 'Fiscal', dataIndex: 'fiscal_status', width: 140, render: (value, record) => <EcfFiscalStatusBadge status={value || record.status} /> },
                { title: 'Proceso', dataIndex: 'job_status', width: 140, render: (value) => <EcfJobStatusBadge status={value || 'idle'} /> },
                { title: 'Error', dataIndex: 'last_error', ellipsis: true, render: (value) => <span className="ecf-error-text">{value}</span> },
                { title: 'Próximo retry', dataIndex: 'next_retry_at', width: 160, render: (value) => value ? moment(value).format('DD/MM/YYYY HH:mm') : <Tag>N/D</Tag> },
              ]}
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sin errores recientes" />
          )}
        </Card>
      </Col>
    </Row>
  );
}

export default EcfAsyncMonitor;
