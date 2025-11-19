import React, { useState } from 'react';
import { AlertCircle, Eye, EyeOff, Lock, User, ShoppingCart } from 'lucide-react';
import { authService } from '../services/api';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
   const navigate = useNavigate();


  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login(formData.username, formData.password);
      const response = await fetch('http://localhost:8000/api/auth/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.username,
          password: formData.password
        })
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        window.location.href = '/home';
      } else {
        setError(data.error || 'Credenciales inválidas');
      }
    } catch (err) {
      setError('Error de conexión. Verifica tu servidor.');
      console.error('Error de login:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const styles = {
    container: {
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    },
    wrapper: {
      width: '100%',
      maxWidth: '420px'
    },
    header: {
      textAlign: 'center',
      marginBottom: '30px'
    },
    logoBox: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '64px',
      height: '64px',
      backgroundColor: '#4F46E5',
      borderRadius: '16px',
      marginBottom: '20px',
      boxShadow: '0 10px 25px rgba(79, 70, 229, 0.3)'
    },
    title: {
      fontSize: '32px',
      fontWeight: 'bold',
      color: 'white',
      marginBottom: '10px',
      textShadow: '0 2px 4px rgba(0,0,0,0.1)'
    },
    subtitle: {
      color: 'rgba(255, 255, 255, 0.9)',
      fontSize: '16px'
    },
    card: {
      backgroundColor: 'white',
      borderRadius: '20px',
      boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
      padding: '40px',
      border: '1px solid rgba(255, 255, 255, 0.1)'
    },
    errorBox: {
      backgroundColor: '#FEE2E2',
      border: '1px solid #FCA5A5',
      borderRadius: '10px',
      padding: '16px',
      display: 'flex',
      gap: '12px',
      marginBottom: '20px'
    },
    errorText: {
      fontSize: '14px',
      color: '#991B1B',
      margin: 0
    },
    inputGroup: {
      marginBottom: '20px'
    },
    label: {
      display: 'block',
      fontSize: '14px',
      fontWeight: '500',
      color: '#374151',
      marginBottom: '8px'
    },
    inputWrapper: {
      position: 'relative'
    },
    icon: {
      position: 'absolute',
      left: '12px',
      top: '50%',
      transform: 'translateY(-50%)',
      color: '#9CA3AF',
      pointerEvents: 'none'
    },
    input: {
      width: '100%',
      paddingLeft: '40px',
      paddingRight: '12px',
      paddingTop: '12px',
      paddingBottom: '12px',
      border: '1px solid #D1D5DB',
      borderRadius: '10px',
      fontSize: '15px',
      transition: 'all 0.2s',
      outline: 'none',
      boxSizing: 'border-box'
    },
    inputFocus: {
      borderColor: '#4F46E5',
      boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.1)'
    },
    passwordWrapper: {
      position: 'relative'
    },
    eyeButton: {
      position: 'absolute',
      right: '12px',
      top: '50%',
      transform: 'translateY(-50%)',
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      padding: '4px',
      display: 'flex',
      alignItems: 'center'
    },
    rememberRow: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '24px'
    },
    checkboxLabel: {
      display: 'flex',
      alignItems: 'center',
      cursor: 'pointer',
      fontSize: '14px',
      color: '#6B7280'
    },
    checkbox: {
      marginRight: '8px',
      cursor: 'pointer'
    },
    forgotLink: {
      fontSize: '14px',
      color: '#4F46E5',
      fontWeight: '500',
      textDecoration: 'none',
      cursor: 'pointer',
      background: 'none',
      border: 'none'
    },
    submitButton: {
      width: '100%',
      backgroundColor: '#4F46E5',
      color: 'white',
      fontWeight: '500',
      padding: '14px',
      borderRadius: '10px',
      border: 'none',
      cursor: 'pointer',
      fontSize: '16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '8px',
      transition: 'background-color 0.2s'
    },
    submitButtonDisabled: {
      opacity: 0.5,
      cursor: 'not-allowed'
    },
    spinner: {
      width: '20px',
      height: '20px',
      border: '2px solid white',
      borderTopColor: 'transparent',
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite'
    },
    footer: {
      marginTop: '24px',
      textAlign: 'center',
      fontSize: '14px',
      color: '#6B7280'
    },
    footerLink: {
      color: '#4F46E5',
      fontWeight: '500',
      cursor: 'pointer',
      background: 'none',
      border: 'none',
      textDecoration: 'none'
    },
    copyright: {
      marginTop: '24px',
      textAlign: 'center',
      fontSize: '13px',
      color: 'rgba(255, 255, 255, 0.8)'
    }
  };

  return (
    <>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        input:focus {
          border-color: #4F46E5 !important;
          box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
        }
        button:hover:not(:disabled) {
          opacity: 0.9;
        }
      `}</style>
      
      <div style={styles.container}>
        <div style={styles.wrapper}>
          {/* Header */}
          <div style={styles.header}>
            <div style={styles.logoBox}>
              <ShoppingCart size={32} color="white" />
            </div>
            <h1 style={styles.title}>Sistema de Facturación</h1>
            <p style={styles.subtitle}>Ingresa tus credenciales para continuar</p>
          </div>

          {/* Card */}
          <div style={styles.card}>
            {/* Error */}
            {error && (
              <div style={styles.errorBox}>
                <AlertCircle size={20} color="#DC2626" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <p style={{ ...styles.errorText, fontWeight: '500', marginBottom: 4 }}>Error</p>
                  <p style={styles.errorText}>{error}</p>
                </div>
              </div>
            )}

            {/* Usuario */}
            <div style={styles.inputGroup}>
              <label style={styles.label}>Usuario</label>
              <div style={styles.inputWrapper}>
                <div style={styles.icon}>
                  <User size={20} />
                </div>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  style={styles.input}
                  placeholder="Ingresa tu usuario"
                />
              </div>
            </div>

            {/* Contraseña */}
            <div style={styles.inputGroup}>
              <label style={styles.label}>Contraseña</label>
              <div style={styles.passwordWrapper}>
                <div style={styles.icon}>
                  <Lock size={20} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  style={{ ...styles.input, paddingRight: '45px' }}
                  placeholder="Ingresa tu contraseña"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={styles.eyeButton}
                >
                  {showPassword ? (
                    <EyeOff size={20} color="#9CA3AF" />
                  ) : (
                    <Eye size={20} color="#9CA3AF" />
                  )}
                </button>
              </div>
            </div>

            {/* Recordar / Olvidaste */}
            <div style={styles.rememberRow}>
              <label style={styles.checkboxLabel}>
                <input type="checkbox" style={styles.checkbox} />
                Recordar sesión
              </label>
              <button
                type="button"
                onClick={() => alert('Contacta al administrador')}
                style={styles.forgotLink}
              >
                ¿Olvidaste tu contraseña?
              </button>
            </div>

            {/* Botón Submit */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              style={{
                ...styles.submitButton,
                ...(loading ? styles.submitButtonDisabled : {})
              }}
            >
              {loading ? (
                <>
                  <div style={styles.spinner}></div>
                  <span>Iniciando sesión...</span>
                </>
              ) : (
                <span>Iniciar Sesión</span>
              )}
            </button>

            {/* Footer */}
            <div style={styles.footer}>
              ¿No tienes cuenta?{' '}
              <button
                type="button"
                onClick={() => alert('Contacta al administrador del sistema')}
                style={styles.footerLink}
              >
                Contacta al administrador
              </button>
            </div>
          </div>

          {/* Copyright */}
          <div style={styles.copyright}>
            © 2025 Sistema de Facturación. Todos los derechos reservados.
          </div>
        </div>
      </div>
    </>
  );
}