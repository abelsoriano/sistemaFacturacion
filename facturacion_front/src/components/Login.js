import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Building2, CheckCircle2, Eye, EyeOff, Lock, ShieldCheck, User } from 'lucide-react';
import { authService } from '../services/api';
import '../css/Login.css';

export default function Login() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login(formData.username, formData.password);
      window.location.href = '/home';
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

  return (
    <main className="login-saas-page">
      <section className="login-brand-panel" aria-label="Presentación del sistema">
        <div className="login-brand-mark">
          <Building2 size={30} />
        </div>
        <span className="login-eyebrow">ASYS ERP SaaS</span>
        <h1>Sistema de facturación e-CF multiempresa</h1>
        <p>
          Opera ventas, inventario, facturación fiscal y procesos DGII desde una
          experiencia preparada para múltiples empresas.
        </p>
        <div className="login-feature-grid">
          <div>
            <ShieldCheck size={18} />
            <span>Acceso seguro</span>
          </div>
          <div>
            <CheckCircle2 size={18} />
            <span>e-CF / DGII</span>
          </div>
          <div>
            <Building2 size={18} />
            <span>Multiempresa</span>
          </div>
        </div>
      </section>

      <section className="login-card-panel" aria-label="Inicio de sesión">
        <div className="login-card">
          <div className="login-card-header">
            <span>Bienvenido</span>
            <h2>Iniciar sesión</h2>
            <p>Ingresa tus credenciales para continuar.</p>
          </div>

          {error && (
            <div className="login-error" role="alert">
              <AlertCircle size={20} />
              <div>
                <strong>Error</strong>
                <p>{error}</p>
              </div>
            </div>
          )}

          <form className="login-form" onSubmit={handleSubmit}>
            <div className="login-field">
              <label htmlFor="username">Usuario</label>
              <div className="login-input-wrap">
                <User size={19} />
                <input
                  id="username"
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="Ingresa tu usuario"
                  autoComplete="username"
                />
              </div>
            </div>

            <div className="login-field">
              <label htmlFor="password">Contraseña</label>
              <div className="login-input-wrap">
                <Lock size={19} />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Ingresa tu contraseña"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-eye-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                </button>
              </div>
            </div>

            <div className="login-options">
              <label>
                <input type="checkbox" />
                Recordar sesión
              </label>
              <button
                type="button"
                onClick={() => alert('Contacta al administrador')}
              >
                ¿Olvidaste tu contraseña?
              </button>
            </div>

            <button type="submit" className="login-submit" disabled={loading}>
              {loading ? (
                <>
                  <span className="login-spinner"></span>
                  Iniciando sesión...
                </>
              ) : (
                'Iniciar sesión'
              )}
            </button>
          </form>

          <div className="login-card-footer">
            <span>¿No tienes cuenta?</span>
            <Link to="/register">Crear cuenta</Link>
          </div>
        </div>

        <p className="login-copyright">
          © 2026 Sistema de Facturación. Todos los derechos reservados.
        </p>
      </section>
    </main>
  );
}
