import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { userHasPermissions } from '../utils/permissions';

/**
 * Componente para proteger rutas que requieren autenticación
 * Uso: <ProtectedRoute><TuComponente /></ProtectedRoute>
 */
export default function ProtectedRoute({ children, permissions = [] }) {
  const [isAuthenticated, setIsAuthenticated] = useState(null); // null = cargando
  const [isAllowed, setIsAllowed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const permissionsKey = permissions.join('|');

  useEffect(() => {
    const verifyToken = async () => {
      const requiredPermissions = permissionsKey ? permissionsKey.split('|') : [];
      const token = localStorage.getItem('token');

      // Si no hay token, no está autenticado
      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      // Verificar que el token sea válido con el backend
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/verify-token/', {
        //  const response = await axios.get('https://7l51msx7-8000.use2.devtunnels.ms/api/verify-token/', {
          headers: { Authorization: `Token ${token}` }
        });
        const user = response.data?.user;
        if (user) {
          localStorage.setItem('user', JSON.stringify(user));
        }
        setIsAuthenticated(true);
        setIsAllowed(userHasPermissions(user, requiredPermissions));
      } catch (error) {
        console.error('Token inválido:', error);
        // Token inválido, limpiar localStorage
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    verifyToken();
  }, [location.pathname, permissionsKey]);

  // Mientras verifica el token, muestra un loading
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{
          width: '50px',
          height: '50px',
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #007bff',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p style={{ color: '#666', fontSize: '16px' }}>Verificando autenticación...</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Si no está autenticado, redirige al login
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (!isAllowed) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f8fafc',
        padding: '24px'
      }}>
        <div style={{
          width: '100%',
          maxWidth: '460px',
          background: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: '12px',
          padding: '28px',
          textAlign: 'center',
          boxShadow: '0 18px 45px rgba(15, 23, 42, 0.08)'
        }}>
          <div style={{
            width: '54px',
            height: '54px',
            borderRadius: '50%',
            background: '#fff7ed',
            color: '#c2410c',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '28px',
            fontWeight: 700,
            marginBottom: '16px'
          }}>!</div>
          <h2 style={{ margin: '0 0 10px', color: '#111827', fontSize: '22px' }}>
            No tienes permiso para entrar
          </h2>
          <p style={{ margin: '0 0 22px', color: '#4b5563', lineHeight: 1.5 }}>
            Tu usuario no tiene el rol o permiso necesario para ver esta pantalla.
            Si necesitas acceso, solicita al administrador que actualice tus roles.
          </p>
          <button
            type="button"
            onClick={() => navigate('/home', { replace: true })}
            style={{
              border: 0,
              borderRadius: '8px',
              background: '#2563eb',
              color: '#fff',
              fontWeight: 600,
              padding: '10px 16px',
              cursor: 'pointer'
            }}
          >
            Volver al inicio
          </button>
        </div>
      </div>
    );
  }

  // Si está autenticado, muestra el componente hijo
  return children;
}


/**
 * Componente alternativo más simple (sin verificación con backend)
 * Solo verifica si existe el token en localStorage
 */
export function SimpleProtectedRoute({ children }) {
  const token = localStorage.getItem('token');

  if (!token) {
    return <Navigate to="/" replace />;
  }

  return children;
}
