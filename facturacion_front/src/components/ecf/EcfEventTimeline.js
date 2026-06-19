import React from 'react';
import { Empty, Timeline, Typography } from 'antd';
import moment from 'moment';

const eventColors = {
  created: 'var(--saas-primary)',
  queued: 'var(--saas-warning)',
  xml_generated: 'var(--saas-primary)',
  signed: 'var(--saas-success)',
  submitted: 'var(--saas-warning)',
  status_checked: 'var(--saas-primary)',
  retry_scheduled: 'var(--saas-warning)',
  skipped: 'var(--saas-muted)',
  accepted: 'var(--saas-success)',
  rejected: 'var(--saas-danger)',
  error: 'var(--saas-danger)',
};

function EcfEventTimeline({ events = [] }) {
  if (!events.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sin eventos" />;
  }

  return (
    <Timeline
      items={events.map((event) => ({
        color: eventColors[event.event_type] || 'var(--saas-primary)',
        children: (
          <div className="ecf-timeline-item">
            <div className="ecf-timeline-head">
              <strong>{event.event_type}</strong>
              <span>{moment(event.created_at).format('DD/MM/YYYY HH:mm:ss')}</span>
            </div>
            {event.message && <Typography.Paragraph className="ecf-timeline-message">{event.message}</Typography.Paragraph>}
            {event.payload && (
              <pre className="ecf-json-block">{JSON.stringify(event.payload, null, 2)}</pre>
            )}
          </div>
        ),
      }))}
    />
  );
}

export default EcfEventTimeline;
