import React from 'react';
import { Button, Dropdown, Modal, Space, Table, Tag, Tooltip, Typography } from 'antd';
import {
  EyeOutlined,
  MoreOutlined,
  ReloadOutlined,
  RetweetOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import moment from 'moment';
import { EcfFiscalStatusBadge, EcfJobStatusBadge } from './EcfStatusBadge';

const resolutionMeta = {
  pending: { color: 'gold', text: 'Pendiente' },
  confirmed: { color: 'green', text: 'Confirmada' },
  rejected: { color: 'red', text: 'Rechazada' },
  resolved: { color: 'blue', text: 'Resuelta' },
};

const inventoryMeta = {
  restored_pending: { color: 'gold', text: 'Pendiente' },
  confirmed: { color: 'green', text: 'Confirmado' },
  compensation_required: { color: 'volcano', text: 'Compensación requerida' },
  compensated: { color: 'blue', text: 'Compensado' },
};

function metaTag(value, metaMap) {
  const meta = metaMap[value] || { color: 'default', text: value || 'N/D' };
  return <Tag color={meta.color}>{meta.text}</Tag>;
}

function E34CreditNoteTable({
  notes,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onOpenDocument,
  actions,
  actionLoading,
}) {
  const confirmReconcile = (record) => {
    Modal.confirm({
      title: 'Compensar inventario',
      icon: <WarningOutlined />,
      content: 'Esta acción descuenta del inventario las cantidades restauradas por una E34 rechazada. El backend bloqueará la operación si detecta actividad posterior o riesgo de inconsistencia.',
      okText: 'Compensar inventario',
      okButtonProps: { danger: true },
      cancelText: 'Cancelar',
      onOk: () => actions.reconcileInventory(record.id),
    });
  };

  const columns = [
    {
      title: 'Nota',
      dataIndex: 'credit_note_number',
      key: 'credit_note_number',
      width: 140,
      fixed: 'left',
      render: (value, record) => (
        <Button type="link" className="ecf-link-button" onClick={() => onOpenDocument(record)}>
          {value || `NC-${record.id}`}
        </Button>
      ),
    },
    {
      title: 'Factura origen',
      dataIndex: 'origin_invoice_number',
      key: 'origin_invoice_number',
      width: 150,
      render: (value) => value || 'N/D',
    },
    {
      title: 'Cliente',
      dataIndex: 'origin_client_name',
      key: 'origin_client_name',
      width: 180,
      ellipsis: true,
      render: (value) => value || 'Consumidor Final',
    },
    {
      title: 'e-NCF E34',
      dataIndex: 'encf',
      key: 'encf',
      width: 160,
      render: (value) => value ? <Typography.Text copyable>{value}</Typography.Text> : <span className="ecf-muted">Pendiente</span>,
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 110,
      align: 'right',
      render: (value) => `$${Number(value || 0).toFixed(2)}`,
    },
    {
      title: 'Estado fiscal',
      dataIndex: 'fiscal_status',
      key: 'fiscal_status',
      width: 150,
      render: (value) => <EcfFiscalStatusBadge status={value} pulse />,
    },
    {
      title: 'Proceso',
      dataIndex: 'job_status',
      key: 'job_status',
      width: 140,
      render: (value) => <EcfJobStatusBadge status={value || 'idle'} pulse />,
    },
    {
      title: 'Resolución',
      dataIndex: 'fiscal_resolution_status',
      key: 'fiscal_resolution_status',
      width: 135,
      render: (value) => metaTag(value, resolutionMeta),
    },
    {
      title: 'Inventario',
      dataIndex: 'inventory_reconciliation_status',
      key: 'inventory_reconciliation_status',
      width: 185,
      render: (value) => metaTag(value, inventoryMeta),
    },
    {
      title: 'Revisión',
      dataIndex: 'requires_manual_review',
      key: 'requires_manual_review',
      width: 125,
      render: (value, record) => value ? (
        <Tooltip title={record.dgii_rejection_reason || 'Requiere revisión manual'}>
          <Tag color="red">Requiere revisión</Tag>
        </Tooltip>
      ) : <Tag>Sin revisión</Tag>,
    },
    {
      title: 'Fecha',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (value) => value ? moment(value).format('DD/MM/YYYY HH:mm') : 'N/D',
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => {
        const items = [
          {
            key: 'open',
            icon: <EyeOutlined />,
            label: 'Ver detalle',
            disabled: !record.electronic_document_id,
            onClick: () => onOpenDocument(record),
          },
          {
            key: 'check',
            icon: <ReloadOutlined />,
            label: 'Consultar DGII',
            disabled: !record.can_check_status,
            onClick: () => actions.checkStatus(record.id),
          },
          {
            key: 'retry',
            icon: <RetweetOutlined />,
            label: 'Reintentar fallo técnico',
            disabled: !record.can_retry,
            onClick: () => actions.retry(record.id),
          },
          {
            key: 'reconcile',
            icon: <WarningOutlined />,
            label: 'Compensar inventario',
            disabled: !record.can_reconcile_inventory,
            onClick: () => confirmReconcile(record),
          },
          {
            key: 'review',
            icon: <SafetyCertificateOutlined />,
            label: 'Marcar revisada',
            disabled: !record.can_mark_reviewed,
            onClick: () => actions.markReviewed(record.id),
          },
        ];

        return (
          <Space>
            <Button size="small" icon={<EyeOutlined />} disabled={!record.electronic_document_id} onClick={() => onOpenDocument(record)} />
            <Dropdown menu={{ items }} trigger={['click']}>
              <Button
                size="small"
                icon={<MoreOutlined />}
                loading={
                  actionLoading[`status-${record.id}`]
                  || actionLoading[`retry-${record.id}`]
                  || actionLoading[`reconcile-${record.id}`]
                  || actionLoading[`review-${record.id}`]
                }
              />
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
      dataSource={notes}
      loading={loading}
      scroll={{ x: 1600 }}
      pagination={{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showTotal: (count, range) => `${range[0]}-${range[1]} de ${count}`,
        onChange: onPageChange,
      }}
      rowClassName={(record) => record.requires_manual_review ? 'e34-review-row' : ''}
    />
  );
}

export default E34CreditNoteTable;
