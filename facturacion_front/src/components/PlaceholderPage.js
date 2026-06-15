import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2 } from 'lucide-react';

export default function PlaceholderPage({
  title,
  subtitle,
  actionLabel,
  actionTo,
  icon: Icon = Building2,
}) {
  const navigate = useNavigate();

  return (
    <section className="saas-placeholder-page">
      <div className="saas-page-header">
        <div>
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actionLabel && actionTo && (
          <button type="button" onClick={() => navigate(actionTo)}>
            {actionLabel}
          </button>
        )}
      </div>

      <div className="saas-empty-state">
        <span>
          <Icon size={30} strokeWidth={1.7} />
        </span>
        <h2>{title}</h2>
        <p>{subtitle || 'Esta sección está preparada para una fase posterior.'}</p>
      </div>
    </section>
  );
}
