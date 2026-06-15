import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Building2, CheckCircle2, Eye, EyeOff, Lock, Mail, ShieldCheck, User } from 'lucide-react';
import { authService } from '../services/api';
import '../css/Login.css';

const initialForm = {
  first_name: '',
  email: '',
  username: '',
  password: '',
  confirm_password: '',
};

export default function Register() {
  const [formData, setFormData] = useState(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const extractError = (err) => {
    const data = err.response?.data;
    if (!data) return 'No pudimos crear la cuenta. Intenta nuevamente.';
    if (typeof data === 'string') return data;
    if (data.detail) return data.detail;
    const firstKey = Object.keys(data)[0];
    const firstValue = firstKey ? data[firstKey] : null;
    if (Array.isArray(firstValue)) return firstValue[0];
    if (typeof firstValue === 'string') return firstValue;
    return 'Revisa los datos del formulario.';
  };

  const handleChange = (event) => {
    setFormData((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (formData.password !== formData.confirm_password) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);
    try {
      await authService.register(formData);
      navigate('/company-onboarding', { replace: true });
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-saas-page">
      <section className="login-brand-panel" aria-label="Registro SaaS">
        <div className="login-brand-mark">
          <Building2 size={30} />
        </div>
        <span className="login-eyebrow">Nuevo espacio SaaS</span>
        <h1>Crea tu cuenta y configura tu primera empresa</h1>
        <p>
          Empieza con un usuario estándar. Luego crearás la empresa activa para
          operar ventas, inventario y facturación e-CF.
        </p>
        <div className="login-feature-grid">
          <div>
            <ShieldCheck size={18} />
            <span>Usuario seguro</span>
          </div>
          <div>
            <Building2 size={18} />
            <span>Primera empresa</span>
          </div>
          <div>
            <CheckCircle2 size={18} />
            <span>Owner inicial</span>
          </div>
        </div>
      </section>

      <section className="login-card-panel" aria-label="Crear cuenta">
        <div className="login-card">
          <div className="login-card-header">
            <span>Registro</span>
            <h2>Crear cuenta</h2>
            <p>Completa tus datos para iniciar el onboarding de empresa.</p>
          </div>

          {error && (
            <div className="login-error" role="alert">
              <AlertCircle size={20} />
              <div>
                <strong>No se pudo registrar</strong>
                <p>{error}</p>
              </div>
            </div>
          )}

          <form className="login-form" onSubmit={handleSubmit}>
            <div className="login-field">
              <label htmlFor="first_name">Nombre</label>
              <div className="login-input-wrap">
                <User size={19} />
                <input
                  id="first_name"
                  type="text"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                  placeholder="Tu nombre"
                  autoComplete="given-name"
                />
              </div>
            </div>

            <div className="login-field">
              <label htmlFor="email">Email</label>
              <div className="login-input-wrap">
                <Mail size={19} />
                <input
                  id="email"
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="tu@email.com"
                  autoComplete="email"
                  required
                />
              </div>
            </div>

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
                  placeholder="Nombre de usuario"
                  autoComplete="username"
                  required
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
                  placeholder="Mínimo 8 caracteres"
                  autoComplete="new-password"
                  required
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

            <div className="login-field">
              <label htmlFor="confirm_password">Confirmar contraseña</label>
              <div className="login-input-wrap">
                <Lock size={19} />
                <input
                  id="confirm_password"
                  type={showPassword ? 'text' : 'password'}
                  name="confirm_password"
                  value={formData.confirm_password}
                  onChange={handleChange}
                  placeholder="Repite tu contraseña"
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

            <button type="submit" className="login-submit" disabled={loading}>
              {loading ? (
                <>
                  <span className="login-spinner"></span>
                  Creando cuenta...
                </>
              ) : (
                'Crear cuenta'
              )}
            </button>
          </form>

          <div className="login-card-footer">
            <span>¿Ya tienes cuenta?</span>
            <Link to="/">Iniciar sesión</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
