import axios from 'axios';

// URL base de tu API
const API_BASE_URL = 'http://127.0.0.1:8000/api';

// Crear instancia de axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================
// INTERCEPTOR DE PETICIONES
// Agrega el token automáticamente a cada request
// ============================================
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ============================================
// INTERCEPTOR DE RESPUESTAS
// Maneja errores 401 (token inválido/expirado)
// ============================================
api.interceptors.response.use(
  (response) => {
    // Si la respuesta es exitosa, retornarla
    return response;
  },
  (error) => {
    // Si el error es 401 (No autorizado)
    if (error.response && error.response.status === 401) {
      console.error('Token inválido o expirado');
      
      // Limpiar localStorage
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // Redirigir al login solo si no estamos ya en login
      if (!window.location.pathname.includes('/')) {
        window.location.href = '/';
      }
    }
    
    // Si el error es 403 (Prohibido)
    if (error.response && error.response.status === 403) {
      console.error('No tienes permisos para realizar esta acción');
    }
    
    return Promise.reject(error);
  }
);

// ============================================
// SERVICIO DE AUTENTICACIÓN
// Funciones auxiliares para login, logout, etc.
// ============================================
export const authService = {
  /**
   * Login de usuario
   */
  login: async (username, password) => {
    try {
      const response = await api.post('/auth/login/', { username, password });
      
      // Guardar token y usuario en localStorage
      if (response.data.token) {
        localStorage.setItem('token', response.data.token);
      }
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
      
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Logout de usuario
   */
  logout: () => {
    // Limpiar localStorage
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // Redirigir al login
    window.location.href = '/';
  },

  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated: () => {
    const token = localStorage.getItem('token');
    return !!token; // Retorna true si hay token, false si no
  },

  /**
   * Obtener usuario actual desde localStorage
   */
  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch (error) {
      console.error('Error al parsear usuario:', error);
      return null;
    }
  },

  /**
   * Obtener token actual
   */
  getToken: () => {
    return localStorage.getItem('token');
  },

  /**
   * Verificar token con el servidor
   */
  verifyToken: async () => {
    try {
      const response = await api.get('/verify-token/');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Actualizar datos del usuario en localStorage
   */
  updateUserData: (userData) => {
    const currentUser = authService.getCurrentUser() || {};
    const updatedUser = { ...currentUser, ...userData };
    localStorage.setItem('user', JSON.stringify(updatedUser));
  }
};

// ============================================
// EXPORTAR API POR DEFECTO
// ============================================
export default api;