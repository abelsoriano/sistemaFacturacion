import React from 'react';
import { Button, Dropdown, Space, Table, Tooltip, Typography } from 'antd';
import {
  CloudUploadOutlined,
  DownloadOutlined,
  EyeOutlined,
  MoreOutlined,
  ReloadOutlined,
  RetweetOutlined,
} from '@ant-design/icons';
import moment from 'moment';
import { ACTIVE_JOB_STATUSES, EcfFiscalStatusBadge, EcfJobStatusBadge, TERMINAL_STATUSES } from './EcfStatusBadge';
import { downloadFiscalArtifact } from '../../services/ecf/ecfApi';

function EcfDocumentTable({
  documents,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onOpen,
  actions,
  actionLoading,
}) {
  const columns = [
    {
      title: 'e-NCF',
      dataIndex: 'encf',
      key: 'encf',
      width: 150,
      fixed: 'left',
      render: (value, record) => (
        <Button type="link" className="ecf-link-button" onClick={() => onOpen(record)}>
          {value}
        </Button>
      ),
    },
    {
      title: 'Factura',
      dataIndex: 'invoice_number',
      key: 'invoice_number',
      width: 130,
      render: (value) => value || 'N/D',
    },
    {
      title: 'Estado fiscal',
      dataIndex: 'fiscal_status',
      key: 'fiscal_status',
      width: 160,
      render: (value, record) => <EcfFiscalStatusBadge status={value || record.status} pulse />,
    },
    {
      title: 'Proceso',
      dataIndex: 'job_status',
      key: 'job_status',
      width: 145,
      render: (value) => <EcfJobStatusBadge status={value || 'idle'} pulse />,
    },
    {
      title: 'TrackID',
      dataIndex: 'track_id',
      key: 'track_id',
      width: 210,
      ellipsis: true,
      render: (value) => value ? <Typography.Text copyable>{value}</Typography.Text> : <span className="ecf-muted">Sin TrackID</span>,
    },
    {
      title: 'Intentos',
      key: 'attempts',
      width: 110,
      render: (_, record) => `${record.submission_attempts || 0}/${record.status_check_attempts || 0}`,
    },
    {
      title: 'Último error',
      dataIndex: 'last_error',
      key: 'last_error',
      ellipsis: true,
      render: (value) => value ? <Tooltip title={value}><span className="ecf-error-text">{value}</span></Tooltip> : <span className="ecf-muted">Ninguno</span>,
    },
    {
      title: 'Actualizado',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (value) => value ? moment(value).format('DD/MM/YYYY HH:mm') : 'N/D',
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => {
        const fiscalStatus = record.fiscal_status || record.status;
        const jobStatus = record.job_status || 'idle';
        const isTerminal = record.is_terminal_fiscal ?? TERMINAL_STATUSES.has(fiscalStatus);
        const hasTrackId = Boolean(record.track_id);
        const canRetry = record.can_retry ?? (!hasTrackId && !isTerminal);
        const canCheckStatus = record.can_check_status ?? (hasTrackId && !isTerminal);
        const canProcess = !isTerminal && !ACTIVE_JOB_STATUSES.has(jobStatus);
        const items = [
          {
            key: 'open',
            icon: <EyeOutlined />,
            label: 'Ver detalle',
            onClick: () => onOpen(record),
          },
          {
            key: 'check',
            icon: <ReloadOutlined />,
            label: 'Consultar DGII',
            disabled: !canCheckStatus,
            onClick: () => actions.checkStatus(record.id),
          },
          {
            key: 'process',
            icon: <CloudUploadOutlined />,
            label: 'Procesar',
            disabled: !canProcess,
            onClick: () => actions.process(record.id),
          },
          {
            key: 'retry',
            icon: <RetweetOutlined />,
            label: 'Reenviar',
            disabled: !canRetry,
            onClick: () => actions.retry(record.id),
          },
          {
            key: 'xml',
            icon: <DownloadOutlined />,
            label: 'XML original',
            disabled: !record.xml_available,
            onClick: () => downloadFiscalArtifact(record.id, 'xml', `${record.encf || 'ecf'}-original.xml`),
          },
          {
            key: 'signed',
            icon: <DownloadOutlined />,
            label: 'XML firmado',
            disabled: !record.signed_xml_available,
            onClick: () => downloadFiscalArtifact(record.id, 'signed-xml', `${record.encf || 'ecf'}-firmado.xml`),
          },
        ];

        return (
          <Space>
            <Button size="small" icon={<EyeOutlined />} onClick={() => onOpen(record)} />
            <Dropdown menu={{ items }} trigger={['click']}>
              <Button size="small" icon={<MoreOutlined />} loading={actionLoading[`process-${record.id}`] || actionLoading[`retry-${record.id}`] || actionLoading[`status-${record.id}`]} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      dataSource={documents}
      loading={loading}
      scroll={{ x: 1200 }}
      pagination={{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showTotal: (count, range) => `${range[0]}-${range[1]} de ${count}`,
        onChange: onPageChange,
      }}
      rowClassName={(record) => ACTIVE_JOB_STATUSES.has(record.job_status) ? 'ecf-active-row' : ''}
    />
  );
}

export default EcfDocumentTable;
