import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PDF_DEFAULT_CONFIG, getSavedPDFConfig, savePDFConfig, resetPDFConfig } from '../utils/pdfConfig';
import '../css/PDFConfig.css'; // Archivo CSS separado para estilos más limpios

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
    setCompany(prev => ({ ...prev, [field]: event.target.value }));
  };

  const handleFooterLineChange = (index) => (event) => {
    const nextLines = [...footerLines];
    nextLines[index] = event.target.value;
    setFooterLines(nextLines);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSaving(true);
    
    // Simular pequeño retraso para mostrar el estado de guardado
    await new Promise(resolve => setTimeout(resolve, 500));
    
    savePDFConfig({ company, footerLines });
    setMessage('✅ Configuración guardada correctamente.');
    
    // Redirigir al home después de 1.5 segundos
    setTimeout(() => {
      navigate('/home');
    }, 1500);
  };

  const handleReset = async () => {
    setIsResetting(true);
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
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
    <div className="pdf-config-container">
      <div className="pdf-config-card">
        {/* Header */}
        <div className="config-header">
          <div className="header-content">
            <div className="header-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 4H20C21.1 4 22 4.9 22 6V18C22 19.1 21.1 20 20 20H4C2.9 20 2 19.1 2 18V6C2 4.9 2.9 4 4 4Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M22 6L12 13L2 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="header-text">
              <h1>Configuración del Ticket PDF</h1>
              <p>Personaliza la información de tu empresa y el pie de página de los tickets</p>
            </div>
          </div>
        </div>

        {/* Message Toast */}
        {message && (
          <div className={`message-toast ${message.includes('✅') ? 'success' : 'info'}`}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Company Section */}
          <div className="config-section">
            <div className="section-header">
              <div className="section-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" stroke="currentColor" strokeWidth="2"/>
                  <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <h2>Información de la Empresa</h2>
            </div>
            
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="companyName">
                  <span className="label-text">Nombre de la empresa</span>
                </label>
                <input
                  id="companyName"
                  type="text"
                  value={company.name}
                  onChange={handleCompanyChange('name')}
                  className="form-input"
                  placeholder="Ej: Mi Empresa S.A."
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="companyPhone">
                  <span className="label-text">Teléfono</span>
                </label>
                <input
                  id="companyPhone"
                  type="text"
                  value={company.phone}
                  onChange={handleCompanyChange('phone')}
                  className="form-input"
                  placeholder="Ej: +123 456 7890"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="companyAddress">
                  <span className="label-text">Dirección</span>
                </label>
                <input
                  id="companyAddress"
                  type="text"
                  value={company.address}
                  onChange={handleCompanyChange('address')}
                  className="form-input"
                  placeholder="Ej: Calle Principal 123"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="companyCity">
                  <span className="label-text">Ciudad</span>
                </label>
                <input
                  id="companyCity"
                  type="text"
                  value={company.city}
                  onChange={handleCompanyChange('city')}
                  className="form-input"
                  placeholder="Ej: Ciudad, País"
                />
              </div>
            </div>
          </div>

          {/* Footer Section */}
          <div className="config-section">
            <div className="section-header">
              <div className="section-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M3 3h18v18H3V3z" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <path d="M7 7h10M7 12h10M7 17h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <h2>Pie de Página</h2>
              <span className="section-badge">Máximo 3 líneas</span>
            </div>
            
            <div className="footer-lines">
              {footerLines.map((line, index) => (
                <div key={index} className="form-group">
                  <label htmlFor={`footerLine${index}`}>
                    <span className="label-text">Línea {index + 1}</span>
                  </label>
                  <input
                    id={`footerLine${index}`}
                    type="text"
                    value={line}
                    onChange={handleFooterLineChange(index)}
                    className="form-input"
                    placeholder={`Texto de la línea ${index + 1}`}
                    maxLength="100"
                  />
                  <span className="input-hint">{line.length}/100 caracteres</span>
                </div>
              ))}
            </div>
          </div>

          {/* Preview Section */}
          <div className="config-section preview-section">
            <div className="section-header">
              <div className="section-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2"/>
                  <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2"/>
                </svg>
              </div>
              <h2>Vista Previa</h2>
            </div>
            <div className="preview-card">
              <div className="preview-content">
                <div className="preview-company">
                  <strong>{company.name || "Nombre de empresa"}</strong>
                  {company.phone && <span>{company.phone}</span>}
                  {company.address && <span>{company.address}</span>}
                  {company.city && <span>{company.city}</span>}
                </div>
                <div className="preview-divider"></div>
                <div className="preview-footer">
                  {footerLines.map((line, idx) => (
                    line && <span key={idx}>{line}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button 
              type="button" 
              onClick={handleCancel}
              className="btn btn-secondary"
            >
              Cancelar
            </button>
            
            <button 
              type="button" 
              onClick={handleReset}
              className="btn btn-outline"
              disabled={isResetting}
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
              className="btn btn-primary"
              disabled={isSaving}
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

export default PDFConfig;