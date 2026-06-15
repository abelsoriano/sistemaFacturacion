import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { userHasPermissions } from '../utils/permissions';
import api, { authService } from '../services/api';
import '../css/SystemState.css';

/**
 * Componente para proteger rutas que requieren autenticación
 * Uso: <ProtectedRoute><TuComponente /></ProtectedRoute>
 */
export default function ProtectedRoute({ children, permissions = [], requireCompany = true }) {
  const [isAuthenticated, setIsAuthenticated] = useState(null); // null = cargando
  const [isAllowed, setIsAllowed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [needsCompanyOnboarding, setNeedsCompanyOnboarding] = useState(false);
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
        const data = await authService.verifyToken();
        const user = data?.user;
        if (user) {
          localStorage.setItem('user', JSON.stringify(user));
        }

        let missingCompany = false;
        if (requireCompany) {
          try {
            const companyResponse = await api.get('/companies/active/');
            const companies = companyResponse.data?.companies || [];
            const activeCompany = companyResponse.data?.active_company || null;
            missingCompany = !activeCompany && companies.length === 0;
            if (missingCompany) {
              localStorage.removeItem('active_company_id');
            }
          } catch (companyError) {
            console.error('No se pudo validar la empresa activa:', companyError);
          }
        }

        setIsAuthenticated(true);
        setIsAllowed(userHasPermissions(user, requiredPermissions));
        setNeedsCompanyOnboarding(missingCompany);
      } catch (error) {
        console.error('Token inválido:', error);
        // Token inválido, limpiar localStorage
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('active_company_id');
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    verifyToken();
  }, [location.pathname, permissionsKey, requireCompany]);

  // Mientras verifica el token, muestra un loading
  if (isLoading) {
    return (
      <SystemStateShell
        tone="loading"
        icon={<span className="system-spinner" />}
        title="Verificando acceso"
        description="Estamos validando tu sesión y permisos antes de abrir esta pantalla."
      >
        <span className="system-state-muted">Verificando autenticación...</span>
      </SystemStateShell>
    );
  }

  // Si no está autenticado, redirige al login
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (needsCompanyOnboarding) {
    return <Navigate to="/company-onboarding" replace state={{ from: location }} />;
  }

  if (!isAllowed) {
    return (
      <SystemStateShell
        tone="warning"
        icon="!"
        title="No tienes permiso para entrar"
        description="Tu usuario no tiene el rol o permiso necesario para ver esta pantalla. Si necesitas acceso, solicita al administrador que actualice tus roles."
      >
        <button
          type="button"
          className="system-state-button"
          onClick={() => navigate('/home', { replace: true })}
        >
          Volver al dashboard
        </button>
      </SystemStateShell>
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

function SystemStateShell({ tone, icon, title, description, children }) {
  return (
    <div className="system-state-page">
      <section className={`system-state-card ${tone || 'info'}`}>
        <div className="system-state-icon">{icon}</div>
        <span className="system-state-eyebrow">Acceso del sistema</span>
        <h1>{title}</h1>
        <p>{description}</p>
        {children && <div className="system-state-actions">{children}</div>}
      </section>
    </div>
  );
}
