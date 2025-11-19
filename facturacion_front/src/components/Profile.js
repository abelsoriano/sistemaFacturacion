import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { FaUser, FaEnvelope, FaSave, FaTimes, FaArrowLeft } from 'react-icons/fa';

const styles = {
  container: {
    maxWidth: 600,
    margin: "40px auto",
    padding: "30px",
    border: "1px solid #e0e0e0",
    borderRadius: "12px",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
    backgroundColor: "#ffffff",
  },
  header: {
    textAlign: "center",
    color: "#333",
    marginBottom: "10px",
    fontSize: "28px",
    fontWeight: "bold"
  },
  subtitle: {
    textAlign: "center",
    color: "#666",
    marginBottom: "30px",
    fontSize: "14px"
  },
  formGroup: {
    marginBottom: "20px",
  },
  label: {
    display: "block",
    marginBottom: "8px",
    fontWeight: "600",
    color: "#555",
    fontSize: "14px"
  },
  inputWrapper: {
    position: "relative",
    display: "flex",
    alignItems: "center"
  },
  icon: {
    position: "absolute",
    left: "12px",
    color: "#999",
    zIndex: 1
  },
  input: {
    width: "100%",
    padding: "12px 12px 12px 40px",
    border: "1px solid #ddd",
    borderRadius: "6px",
    boxSizing: "border-box",
    fontSize: "15px",
    transition: "border-color 0.3s",
    outline: "none"
  },
  buttonGroup: {
    display: "flex",
    gap: "10px",
    marginTop: "30px"
  },
  button: {
    flex: 1,
    padding: "12px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "15px",
    fontWeight: "600",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    transition: "all 0.3s"
  },
  buttonPrimary: {
    backgroundColor: "#007bff",
    color: "white",
  },
  buttonSecondary: {
    backgroundColor: "#6c757d",
    color: "white",
  },
  backButton: {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 16px",
    backgroundColor: "transparent",
    border: "1px solid #ddd",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
    color: "#666",
    marginBottom: "20px",
    transition: "all 0.3s"
  },
  avatar: {
    width: "80px",
    height: "80px",
    borderRadius: "50%",
    backgroundColor: "#007bff",
    color: "white",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "32px",
    fontWeight: "bold",
    margin: "0 auto 20px",
    border: "4px solid #e3f2fd"
  },
  alert: {
    padding: "12px 16px",
    borderRadius: "6px",
    marginBottom: "20px",
    display: "flex",
    alignItems: "center",
    gap: "10px"
  },
  alertSuccess: {
    backgroundColor: "#d4edda",
    color: "#155724",
    border: "1px solid #c3e6cb"
  },
  alertError: {
    backgroundColor: "#f8d7da",
    color: "#721c24",
    border: "1px solid #f5c6cb"
  }
};

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

    axios.get("http://127.0.0.1:8000/api/profile/", {
      headers: { Authorization: `Token ${token}` }
    })
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
    
    axios.put("http://127.0.0.1:8000/api/profile/", formData, {
      headers: { Authorization: `Token ${token}` }
    })
    .then(res => {
      setSuccess(true);
      
      // Actualizar localStorage con los nuevos datos
      const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
      const updatedUser = {
        ...currentUser,
        first_name: res.data.user.first_name,
        last_name: res.data.user.last_name,
        email: res.data.user.email
      };
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      // Redirigir después de 1.5 segundos
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
      <div style={styles.container}>
        <p style={styles.header}>Cargando perfil...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <button 
        onClick={handleCancel}
        style={styles.backButton}
        onMouseEnter={(e) => {
          e.target.style.backgroundColor = "#f8f9fa";
          e.target.style.borderColor = "#999";
        }}
        onMouseLeave={(e) => {
          e.target.style.backgroundColor = "transparent";
          e.target.style.borderColor = "#ddd";
        }}
      >
        <FaArrowLeft /> Volver al Dashboard
      </button>

      <div style={styles.avatar}>
        {getUserInitials()}
      </div>

      <h2 style={styles.header}>Perfil de Usuario</h2>
      <p style={styles.subtitle}>@{formData.username}</p>

      {success && (
        <div style={{...styles.alert, ...styles.alertSuccess}}>
          <span>✓</span>
          <span>¡Perfil actualizado correctamente! Redirigiendo...</span>
        </div>
      )}

      {error && (
        <div style={{...styles.alert, ...styles.alertError}}>
          <span>✗</span>
          <span>{error}</span>
        </div>
      )}

      <div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Nombre</label>
          <div style={styles.inputWrapper}>
            <FaUser style={styles.icon} />
            <input
              type="text"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              style={styles.input}
              placeholder="Ingresa tu nombre"
              onFocus={(e) => e.target.style.borderColor = "#007bff"}
              onBlur={(e) => e.target.style.borderColor = "#ddd"}
            />
          </div>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Apellido</label>
          <div style={styles.inputWrapper}>
            <FaUser style={styles.icon} />
            <input
              type="text"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              style={styles.input}
              placeholder="Ingresa tu apellido"
              onFocus={(e) => e.target.style.borderColor = "#007bff"}
              onBlur={(e) => e.target.style.borderColor = "#ddd"}
            />
          </div>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Correo Electrónico</label>
          <div style={styles.inputWrapper}>
            <FaEnvelope style={styles.icon} />
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              style={styles.input}
              placeholder="correo@ejemplo.com"
              onFocus={(e) => e.target.style.borderColor = "#007bff"}
              onBlur={(e) => e.target.style.borderColor = "#ddd"}
            />
          </div>
        </div>

        <div style={styles.buttonGroup}>
          <button 
            type="button"
            onClick={handleCancel}
            style={{...styles.button, ...styles.buttonSecondary}}
            disabled={saving}
            onMouseEnter={(e) => !saving && (e.target.style.backgroundColor = "#5a6268")}
            onMouseLeave={(e) => !saving && (e.target.style.backgroundColor = "#6c757d")}
          >
            <FaTimes /> Cancelar
          </button>
          
          <button 
            type="button"
            onClick={handleSubmit}
            style={{
              ...styles.button, 
              ...styles.buttonPrimary,
              opacity: (!hasChanges() || saving) ? 0.6 : 1,
              cursor: (!hasChanges() || saving) ? "not-allowed" : "pointer"
            }}
            disabled={!hasChanges() || saving}
            onMouseEnter={(e) => hasChanges() && !saving && (e.target.style.backgroundColor = "#0056b3")}
            onMouseLeave={(e) => hasChanges() && !saving && (e.target.style.backgroundColor = "#007bff")}
          >
            {saving ? (
              <>Guardando...</>
            ) : (
              <>
                <FaSave /> Guardar Cambios
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}