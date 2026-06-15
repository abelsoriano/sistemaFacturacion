import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PDF_DEFAULT_CONFIG, getSavedPDFConfig, savePDFConfig, resetPDFConfig } from '../utils/pdfConfig';
import '../css/PDFConfig.css';

const STYLE_TOKENS = [
  { label: 'Primario', value: '#6C63FF' },
  { label: 'Navbar', value: '#1B1A2E' },
  { label: 'Activo', value: '#EEEDFE' },
];

function PDFConfig() {
  const navigate = useNavigate();
  const [company, setCompany] = useState(PDF_DEFAULT_CONFIG.company);
  const [footerLines, setFooterLines] = useState(PDF_DEFAULT_CONFIG.footerLines);
  const [message, setMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => {
    const savedConfig = getSavedPDFConfig();
    if (savedConfig.company) {
      setCompany({ ...PDF_DEFAULT_CONFIG.company, ...savedConfig.company });
    }
    if (Array.isArray(savedConfig.footerLines)) {
      setFooterLines(savedConfig.footerLines);
    }
  }, []);

  const handleCompanyChange = (field) => (event) => {
    setCompany((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const handleFooterLineChange = (index) => (event) => {
    const nextLines = [...footerLines];
    nextLines[index] = event.target.value;
    setFooterLines(nextLines);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSaving(true);

    await new Promise((resolve) => setTimeout(resolve, 500));

    savePDFConfig({ company, footerLines });
    setMessage('✅ Configuración guardada correctamente.');

    setTimeout(() => {
      navigate('/home');
    }, 1500);
  };

  const handleReset = async () => {
    setIsResetting(true);

    await new Promise((resolve) => setTimeout(resolve, 300));

    resetPDFConfig();
    setCompany(PDF_DEFAULT_CONFIG.company);
    setFooterLines(PDF_DEFAULT_CONFIG.footerLines);
    setMessage('🔄 Valores por defecto restaurados.');

    setTimeout(() => setMessage(''), 3000);
    setIsResetting(false);
  };

  const handleCancel = () => {
    navigate('/home');
  };

  return (
    <div className="pdf-config-page">
      <div className="pdf-config-shell">
        <header className="pdf-config-hero">
          <div>
            <span className="pdf-config-eyebrow">Configuración</span>
            <h1>Configuración PDF y tickets</h1>
            <p>
              Ajusta los datos visibles en comprobantes impresos y tickets locales.
              Esta configuración se guarda en el navegador.
            </p>
          </div>
          <div className="pdf-config-hero-badge">
            <span>LocalStorage</span>
            <strong>Vista local</strong>
          </div>
        </header>

        {message && (
          <div className={`pdf-config-message ${message.includes('✅') ? 'success' : 'info'}`}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="pdf-config-form">
          <section className="pdf-config-layout">
            <div className="pdf-config-main">
              <div className="pdf-config-section">
                <div className="pdf-config-section-head">
                  <div>
                    <span className="section-kicker">Empresa</span>
                    <h2>Datos visibles</h2>
                  </div>
                  <span className="section-status">Ticket / factura</span>
                </div>

                <div className="pdf-config-grid">
                  <div className="pdf-config-field">
                    <label htmlFor="companyName">Nombre comercial</label>
                    <input
                      id="companyName"
                      type="text"
                      value={company.name}
                      onChange={handleCompanyChange('name')}
                      placeholder="Ej: PERCY TECHNOLOGY"
                      maxLength={60}
                    />
                    <small>{company.name.length}/60 caracteres</small>
                  </div>

                  <div className="pdf-config-field">
                    <label htmlFor="companyPhone">Teléfono</label>
                    <input
                      id="companyPhone"
                      type="text"
                      value={company.phone}
                      onChange={handleCompanyChange('phone')}
                      placeholder="Ej: (809) 986-6178"
                      maxLength={30}
                    />
                    <small>{company.phone.length}/30 caracteres</small>
                  </div>

                  <div className="pdf-config-field full-width">
                    <label htmlFor="companyAddress">Dirección</label>
                    <input
                      id="companyAddress"
                      type="text"
                      value={company.address}
                      onChange={handleCompanyChange('address')}
                      placeholder="Dirección completa"
                      maxLength={100}
                    />
                    <small>{company.address.length}/100 caracteres</small>
                  </div>

                  <div className="pdf-config-field full-width">
                    <label htmlFor="companyCity">Ciudad / país</label>
                    <input
                      id="companyCity"
                      type="text"
                      value={company.city}
                      onChange={handleCompanyChange('city')}
                      placeholder="Ciudad, país"
                      maxLength={60}
                    />
                    <small>{company.city.length}/60 caracteres</small>
                  </div>
                </div>
              </div>

              <div className="pdf-config-section">
                <div className="pdf-config-section-head">
                  <div>
                    <span className="section-kicker">Ticket / factura</span>
                    <h2>Mensajes de cierre</h2>
                  </div>
                  <span className="section-status">Máximo 3 líneas</span>
                </div>

                <div className="pdf-config-footer-lines">
                  {footerLines.map((line, index) => (
                    <div key={index} className="pdf-config-field">
                      <label htmlFor={`footer-${index}`}>Línea {index + 1}</label>
                      <input
                        id={`footer-${index}`}
                        type="text"
                        value={line}
                        onChange={handleFooterLineChange(index)}
                        placeholder={`Texto de la línea ${index + 1}`}
                        maxLength={100}
                      />
                      <small>{line.length}/100 caracteres</small>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <aside className="pdf-config-side">
              <div className="pdf-config-section compact">
                <div className="pdf-config-section-head">
                  <div>
                    <span className="section-kicker">Logo</span>
                    <h2>Branding local</h2>
                  </div>
                </div>
                <div className="pdf-logo-preview">
                  <span>{getInitials(company.name)}</span>
                </div>
                <p className="pdf-config-help">
                  La carga de logo por empresa se conectará en una fase posterior.
                </p>
              </div>

              <div className="pdf-config-section compact">
                <div className="pdf-config-section-head">
                  <div>
                    <span className="section-kicker">Estilo</span>
                    <h2>Paleta SaaS</h2>
                  </div>
                </div>
                <div className="pdf-token-list">
                  {STYLE_TOKENS.map((token) => (
                    <div className="pdf-token-row" key={token.label}>
                      <span style={{ backgroundColor: token.value }}></span>
                      <div>
                        <strong>{token.label}</strong>
                        <small>{token.value}</small>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pdf-config-section compact">
                <div className="pdf-config-section-head">
                  <div>
                    <span className="section-kicker">Previsualización</span>
                    <h2>Ticket ejemplo</h2>
                  </div>
                </div>
                <div className="pdf-preview-ticket">
                  <div className="pdf-preview-header">
                    <h3>{company.name || 'Nombre de la empresa'}</h3>
                    <p>{company.address || 'Dirección'}</p>
                    <p>{company.phone || 'Teléfono'}</p>
                    <p>{company.city || 'Ciudad'}</p>
                  </div>
                  <div className="pdf-preview-divider"></div>
                  <div className="pdf-preview-content">
                    <p><strong>Factura No.</strong> 001234</p>
                    <p><strong>Fecha</strong> {new Date().toLocaleDateString('es-ES')}</p>
                    <p><strong>Cliente</strong> Cliente de ejemplo</p>
                  </div>
                  <div className="pdf-preview-divider"></div>
                  <div className="pdf-preview-footer">
                    {footerLines.map((line, index) => (
                      line.trim() ? <p key={index}>{line}</p> : null
                    ))}
                    {footerLines.every((line) => !line.trim()) && (
                      <p className="pdf-preview-muted">Sin mensaje</p>
                    )}
                  </div>
                </div>
              </div>
            </aside>
          </section>

          <div className="pdf-config-actions">
            <button
              type="button"
              onClick={handleCancel}
              className="pdf-config-btn secondary"
              disabled={isSaving || isResetting}
            >
              Cancelar
            </button>

            <button
              type="button"
              onClick={handleReset}
              className="pdf-config-btn warning"
              disabled={isResetting || isSaving}
            >
              {isResetting ? (
                <>
                  <span className="spinner"></span>
                  Restaurando...
                </>
              ) : (
                'Restaurar valores'
              )}
            </button>

            <button
              type="submit"
              className="pdf-config-btn primary"
              disabled={isSaving || isResetting}
            >
              {isSaving ? (
                <>
                  <span className="spinner"></span>
                  Guardando...
                </>
              ) : (
                'Guardar configuración'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function getInitials(name) {
  const cleanName = String(name || '').trim();
  if (!cleanName) return 'PDF';
  return cleanName
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

export default PDFConfig;
