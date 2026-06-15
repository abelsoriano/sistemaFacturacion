import React from 'react';
import { Button, DatePicker, Input, Select, Space } from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';

const fiscalStatusOptions = [
  { value: 'draft', label: 'Borrador' },
  { value: 'xml_generated', label: 'XML generado' },
  { value: 'signed', label: 'Firmado' },
  { value: 'submitted', label: 'Enviado' },
  { value: 'accepted', label: 'Aceptado' },
  { value: 'rejected', label: 'Rechazado' },
];

const jobStatusOptions = [
  { value: 'idle', label: 'Inactivo' },
  { value: 'queued', label: 'En cola' },
  { value: 'running', label: 'Ejecutando' },
  { value: 'retrying', label: 'Reintentando' },
  { value: 'failed', label: 'Fallido' },
];

const resolutionOptions = [
  { value: 'pending', label: 'Pendiente' },
  { value: 'confirmed', label: 'Confirmada' },
  { value: 'rejected', label: 'Rechazada' },
  { value: 'resolved', label: 'Resuelta' },
];

const inventoryOptions = [
  { value: 'restored_pending', label: 'Pendiente' },
  { value: 'confirmed', label: 'Confirmado' },
  { value: 'compensation_required', label: 'Compensación requerida' },
  { value: 'compensated', label: 'Compensado' },
];

function E34CreditNoteFilters({ filters, onChange, onRefresh, loading }) {
  const patch = (field, value) => onChange({ ...filters, [field]: value === '' ? undefined : value });
  const patchDates = (dates) => {
    onChange({
      ...filters,
      created_at_from: dates?.[0] ? dates[0].format('YYYY-MM-DD') : undefined,
      created_at_to: dates?.[1] ? dates[1].format('YYYY-MM-DD') : undefined,
    });
  };

  return (
    <div className="ecf-filter-bar e34-filter-bar">
      <Input
        allowClear
        prefix={<SearchOutlined />}
        placeholder="Buscar nota, factura, cliente o e-NCF"
        value={filters.search}
        onChange={(event) => patch('search', event.target.value)}
        className="ecf-search"
      />
      <Space wrap>
        <Select allowClear placeholder="Fiscal" value={filters.ecf_fiscal_status} onChange={(value) => patch('ecf_fiscal_status', value)} options={fiscalStatusOptions} className="ecf-select" />
        <Select allowClear placeholder="Proceso" value={filters.ecf_job_status} onChange={(value) => patch('ecf_job_status', value)} options={jobStatusOptions} className="ecf-select" />
        <Select allowClear placeholder="Resolución" value={filters.fiscal_resolution_status} onChange={(value) => patch('fiscal_resolution_status', value)} options={resolutionOptions} className="ecf-select" />
        <Select allowClear placeholder="Inventario" value={filters.inventory_reconciliation_status} onChange={(value) => patch('inventory_reconciliation_status', value)} options={inventoryOptions} className="ecf-select" />
        <Select
          allowClear
          placeholder="Revisión"
          value={filters.requires_manual_review}
          onChange={(value) => patch('requires_manual_review', value)}
          options={[
            { value: true, label: 'Requiere revisión' },
            { value: false, label: 'Sin revisión' },
          ]}
          className="ecf-select"
        />
        <Input allowClear placeholder="Cliente ID" value={filters.client} onChange={(event) => patch('client', event.target.value)} className="ecf-select" />
        <DatePicker.RangePicker onChange={patchDates} />
        <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading}>
          Actualizar
        </Button>
      </Space>
    </div>
  );
}

export default E34CreditNoteFilters;
