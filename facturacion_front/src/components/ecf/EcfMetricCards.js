import React from 'react';
import { Card, Col, Progress, Row, Statistic } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloudSyncOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';

const countStatus = (items = [], status, key = 'status') => {
  const row = items.find((item) => item[key] === status);
  return Number(row?.count || 0);
};

function EcfMetricCards({ monitor }) {
  const fiscalRows = monitor?.by_fiscal_status || monitor?.by_status || [];
  const jobRows = monitor?.by_job_status || [];
  const accepted = monitor?.accepted ?? countStatus(fiscalRows, 'accepted', fiscalRows[0]?.fiscal_status !== undefined ? 'fiscal_status' : 'status');
  const rejected = monitor?.rejected ?? countStatus(fiscalRows, 'rejected', fiscalRows[0]?.fiscal_status !== undefined ? 'fiscal_status' : 'status');
  const submitted = monitor?.submitted ?? countStatus(fiscalRows, 'submitted', fiscalRows[0]?.fiscal_status !== undefined ? 'fiscal_status' : 'status');
  const queued = monitor?.queued ?? countStatus(jobRows, 'queued', 'job_status');
  const running = monitor?.running ?? countStatus(jobRows, 'running', 'job_status');
  const retrying = monitor?.retrying ?? countStatus(jobRows, 'retrying', 'job_status');
  const processing = submitted + queued + running + retrying;
  const technicalFailed = monitor?.technical_failed ?? countStatus(jobRows, 'failed', 'job_status');
  const total = fiscalRows.reduce((sum, item) => sum + Number(item.count || 0), 0);
  const acceptanceRate = total ? Math.round((accepted / total) * 100) : 0;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} xl={6}>
        <Card className="ecf-metric-card" bordered={false}>
          <Statistic title="Aceptados" value={accepted} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#12805c' }} />
          <Progress percent={acceptanceRate} showInfo={false} strokeColor="#12805c" />
          <div className="ecf-muted">{acceptanceRate}% tasa aceptación</div>
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className="ecf-metric-card" bordered={false}>
          <Statistic title="Procesando" value={processing} prefix={<CloudSyncOutlined />} valueStyle={{ color: '#1d4ed8' }} />
          <Progress percent={Math.min(100, processing * 10)} showInfo={false} strokeColor="#1d4ed8" />
          <div className="ecf-muted">{submitted} enviados, {queued + running + retrying} técnicos</div>
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className="ecf-metric-card" bordered={false}>
          <Statistic title="Rechazados DGII" value={rejected} prefix={<ExclamationCircleOutlined />} valueStyle={{ color: '#b42318' }} />
          <Progress percent={Math.min(100, rejected * 10)} showInfo={false} strokeColor="#b42318" />
          <div className="ecf-muted">Estado fiscal terminal</div>
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={6}>
        <Card className="ecf-metric-card" bordered={false}>
          <Statistic title="Fallos técnicos" value={technicalFailed} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#b54708' }} />
          <Progress percent={Math.min(100, technicalFailed * 10)} showInfo={false} strokeColor="#b54708" />
          <div className="ecf-muted">{monitor?.retry_pending || 0} retries pendientes</div>
        </Card>
      </Col>
    </Row>
  );
}

export default EcfMetricCards;
