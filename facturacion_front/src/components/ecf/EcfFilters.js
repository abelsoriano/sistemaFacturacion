import React from 'react';
import { Button, Input, Select, Space } from 'antd';
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

const typeOptions = [
  { value: '31', label: 'e-CF 31' },
  { value: '32', label: 'e-CF 32' },
  { value: '33', label: 'e-CF 33' },
  { value: '34', label: 'e-CF 34' },
  { value: '41', label: 'e-CF 41' },
  { value: '43', label: 'e-CF 43' },
  { value: '44', label: 'e-CF 44' },
  { value: '45', label: 'e-CF 45' },
  { value: '46', label: 'e-CF 46' },
  { value: '47', label: 'e-CF 47' },
];

function EcfFilters({ filters, onChange, onRefresh, loading }) {
  const patch = (field, value) => onChange({ ...filters, [field]: value || undefined });

  return (
    <div className="ecf-filter-bar">
      <Input
        allowClear
        prefix={<SearchOutlined />}
        placeholder="Buscar e-NCF, TrackID o factura"
        value={filters.search}
        onChange={(event) => patch('search', event.target.value)}
        className="ecf-search"
      />
      <Space wrap>
        <Select
          allowClear
          placeholder="Estado fiscal"
          value={filters.fiscal_status || filters.status}
          onChange={(value) => patch('fiscal_status', value)}
          options={fiscalStatusOptions}
          className="ecf-select"
        />
        <Select
          allowClear
          placeholder="Proceso"
          value={filters.job_status}
          onChange={(value) => patch('job_status', value)}
          options={jobStatusOptions}
          className="ecf-select"
        />
        <Select
          allowClear
          placeholder="Tipo"
          value={filters.ecf_type}
          onChange={(value) => patch('ecf_type', value)}
          options={typeOptions}
          className="ecf-select"
        />
        <Select
          value={filters.ordering}
          onChange={(value) => patch('ordering', value)}
          options={[
            { value: '-created_at', label: 'Recientes' },
            { value: 'created_at', label: 'Antiguos' },
            { value: 'encf', label: 'e-NCF' },
            { value: '-updated_at', label: 'Actualizados' },
          ]}
          className="ecf-select"
        />
        <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading}>
          Actualizar
        </Button>
      </Space>
    </div>
  );
}

export default EcfFilters;
