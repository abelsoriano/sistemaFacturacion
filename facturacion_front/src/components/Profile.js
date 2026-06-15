import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaArrowLeft, FaEnvelope, FaIdBadge, FaSave, FaShieldAlt, FaTimes, FaUser } from 'react-icons/fa';
import api, { authService } from '../services/api';
import '../css/Profile.css';

export default function Profile() {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    username: ""
  });
  const [originalData, setOriginalData] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  const getUserInitials = () => {
    if (formData.first_name && formData.last_name) {
      return `${formData.first_name[0]}${formData.last_name[0]}`.toUpperCase();
    }
    if (formData.username) {
      return formData.username.substring(0, 2).toUpperCase();
    }
    return "US";
  };

  useEffect(() => {
    if (!token) {
      setError("No hay token de autenticación.");
      setLoading(false);
      navigate('/');
      return;
    }

    api.get("/profile/")
      .then(res => {
        const userData = {
          first_name: res.data.first_name || "",
          last_name: res.data.last_name || "",
          email: res.data.email || "",
          username: res.data.username || ""
        };
        setFormData(userData);
        setOriginalData(userData);
      })
      .catch(err => {
        console.error("Error al cargar el perfil:", err);
        setError("No se pudo cargar el perfil.");
        if (err.response?.status === 401) {
          navigate('/');
        }
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token, navigate]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError(null);
    setSuccess(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (loading || saving) return;

    setSaving(true);
    setError(null);

    api.put("/profile/", formData)
      .then(res => {
        setSuccess(true);

        const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
        const updatedUser = {
          ...currentUser,
          first_name: res.data.user.first_name,
          last_name: res.data.user.last_name,
          email: res.data.user.email
        };
        localStorage.setItem('user', JSON.stringify(updatedUser));
        authService.updateUserData(updatedUser);

        setTimeout(() => {
          navigate('/home');
        }, 1500);
      })
      .catch(err => {
        console.error("Error al actualizar el perfil:", err);
        setError(err.response?.data?.message || "Error al actualizar el perfil");
      })
      .finally(() => {
        setSaving(false);
      });
  };

  const handleCancel = () => {
    navigate('/home');
  };

  const hasChanges = () => {
    return JSON.stringify(formData) !== JSON.stringify(originalData);
  };

  if (loading) {
    return (
      <div className="profile-page">
        <div className="profile-loading-card">
          <span className="profile-spinner"></span>
          <p>Cargando perfil...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-shell">
        <header className="profile-hero">
          <button type="button" className="profile-back-btn" onClick={handleCancel}>
            <FaArrowLeft /> Volver
          </button>
          <div className="profile-title-block">
            <span className="profile-eyebrow">Mi cuenta</span>
            <h1>Perfil de usuario</h1>
            <p>Administra tu información personal visible dentro del ERP.</p>
          </div>
        </header>

        {success && (
          <div className="profile-alert success">
            <span>✓</span>
            <span>Perfil actualizado correctamente. Redirigiendo...</span>
          </div>
        )}

        {error && (
          <div className="profile-alert error">
            <span>✗</span>
            <span>{error}</span>
          </div>
        )}

        <div className="profile-layout">
          <aside className="profile-summary-card">
            <div className="profile-avatar">{getUserInitials()}</div>
            <h2>{fullName(formData) || formData.username || 'Usuario'}</h2>
            <p>@{formData.username || 'sin_usuario'}</p>

            <div className="profile-info-list">
              <div>
                <FaIdBadge />
                <span>Usuario</span>
                <strong>{formData.username || 'No definido'}</strong>
              </div>
              <div>
                <FaEnvelope />
                <span>Correo</span>
                <strong>{formData.email || 'No definido'}</strong>
              </div>
            </div>
          </aside>

          <main className="profile-main">
            <form className="profile-card" onSubmit={handleSubmit}>
              <div className="profile-card-header">
                <div>
                  <span>Información personal</span>
                  <h2>Datos del usuario</h2>
                </div>
                <FaUser />
              </div>

              <div className="profile-form-grid">
                <div className="profile-field">
                  <label htmlFor="first_name">Nombre</label>
                  <div className="profile-input-wrap">
                    <FaUser />
                    <input
                      id="first_name"
                      type="text"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleChange}
                      placeholder="Ingresa tu nombre"
                    />
                  </div>
                </div>

                <div className="profile-field">
                  <label htmlFor="last_name">Apellido</label>
                  <div className="profile-input-wrap">
                    <FaUser />
                    <input
                      id="last_name"
                      type="text"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleChange}
                      placeholder="Ingresa tu apellido"
                    />
                  </div>
                </div>

                <div className="profile-field full-width">
                  <label htmlFor="email">Correo electrónico</label>
                  <div className="profile-input-wrap">
                    <FaEnvelope />
                    <input
                      id="email"
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="correo@ejemplo.com"
                    />
                  </div>
                </div>
              </div>

              <div className="profile-actions">
                <button type="button" className="profile-btn secondary" onClick={handleCancel} disabled={saving}>
                  <FaTimes /> Cancelar
                </button>
                <button type="submit" className="profile-btn primary" disabled={!hasChanges() || saving}>
                  {saving ? (
                    <>Guardando...</>
                  ) : (
                    <>
                      <FaSave /> Guardar cambios
                    </>
                  )}
                </button>
              </div>
            </form>

            <section className="profile-card profile-security-card">
              <div className="profile-card-header">
                <div>
                  <span>Seguridad</span>
                  <h2>Cuenta y acceso</h2>
                </div>
                <FaShieldAlt />
              </div>
              <div className="profile-security-grid">
                <div>
                  <strong>Sesión activa</strong>
                  <p>Tu acceso usa el token de autenticación actual.</p>
                </div>
                <div>
                  <strong>Cambio de contraseña</strong>
                  <p>Disponible en una próxima fase de seguridad de cuenta.</p>
                </div>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
}

function fullName(user) {
  return [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
}
