import React, { useState, useEffect } from 'react';
import { authService } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { 
  FaTags, 
  FaBoxOpen, 
  FaShoppingCart, 
  FaWarehouse, 
  FaFileInvoice, 
  FaHandshake,
  FaChartLine,
  FaClipboardList,
  FaUserFriends,
  FaCog,
  FaSearch,
  FaSignOutAlt,
  FaUser,
  FaBell,
  FaAngleDown
} from 'react-icons/fa';
import { Link } from "react-router-dom";
import api from '../services/api';
import HomeConfig from '../components/HomeConfig';

function Home() {
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState({
    ventasHoy: 0,
    productosBajoStock: 0,
    facturasPendientes: 0,
    ingresosMensuales: "0"
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showConfig, setShowConfig] = useState(false);
  const [homeConfig, setHomeConfig] = useState({});
  const [categoryOrder, setCategoryOrder] = useState([]);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const navigate = useNavigate();

  // Cargar usuario actual
  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setCurrentUser(user);
  }, []);

  // Cargar configuración y orden al iniciar
  useEffect(() => {
    const savedConfig = JSON.parse(localStorage.getItem('homeConfig') || '{}');
    const savedOrder = JSON.parse(localStorage.getItem('homeItemOrder') || '[]');
    setHomeConfig(savedConfig);
    setCategoryOrder(savedOrder);
  }, []);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        const today = new Date().toISOString().split('T')[0];
        const dashboardResponse = await api.get('/dashboard/');
        const dashboardData = dashboardResponse.data;  
        
        if (!dashboardData || !dashboardData.salesSummary || !dashboardData.inventoryStatus) {
          throw new Error('Datos del dashboard con formato inesperado');
        }
        
        let facturasPendientes = 0;
        try {
          const invoicesResponse = await api.get('/invoices/?status=pending');
          const invoicesData = invoicesResponse.data;
          facturasPendientes = Array.isArray(invoicesData) ? invoicesData.length : 0;
        } catch (invoiceErr) {
          console.warn("Error al obtener facturas pendientes:", invoiceErr);
        }
        
        let todaySales = 0;
        if (dashboardData.recentSales && Array.isArray(dashboardData.recentSales)) {
          todaySales = dashboardData.recentSales.filter(sale => 
            sale.date && sale.date.startsWith && sale.date.startsWith(today)
          ).length;
        }
        
        let productosBajoStock = 0;
        if (dashboardData.inventoryStatus && 
            typeof dashboardData.inventoryStatus.low_stock_count === 'number') {
          productosBajoStock = dashboardData.inventoryStatus.low_stock_count;
        }
        
        let ingresosMensuales = "0";
        if (dashboardData.salesSummary && 
            (typeof dashboardData.salesSummary.total_sales === 'number' || 
             typeof dashboardData.salesSummary.total_sales === 'string')) {
          const totalSales = parseFloat(dashboardData.salesSummary.total_sales) || 0;
          ingresosMensuales = new Intl.NumberFormat('es-MX').format(totalSales);
        }
        
        const newStats = {
          ventasHoy: todaySales,
          productosBajoStock: productosBajoStock,
          facturasPendientes: facturasPendientes,
          ingresosMensuales: ingresosMensuales
        };
        
        setStats(newStats);
        setLoading(false);
      } catch (err) {
        console.error("Error al cargar datos:", err);
        setError(err.message);
        setLoading(false);
        
        setStats({
          ventasHoy: 0,
          productosBajoStock: 0,
          facturasPendientes: 0,
          ingresosMensuales: "0"
        });
      }
    };

    fetchDashboardData();
  }, []);

  const menuItems = [
    {
      id: 'inventoryCategory',
      category: "Inventario",
      colorClass: "primary",
      items: [
        { 
          id: 'products',
          title: "Productos", 
          icon: <FaBoxOpen size={28} />, 
          description: "Gestiona el catálogo de productos", 
          route: "/productsList",
          colorClass: "success" 
        },
        { 
          id: 'categories',
          title: "Categorías", 
          icon: <FaTags size={28} />, 
          description: "Administra categorías de productos", 
          route: "/categoriaList",
          colorClass: "primary" 
        },
        { 
          id: 'warehouse',
          title: "Almacén", 
          icon: <FaWarehouse size={28} />, 
          description: "Control de inventario y stock", 
          route: "/list-item",
          colorClass: "dark" 
        }
      ]
    },
    {
      id: 'salesCategory',
      category: "Ventas",
      colorClass: "success",
      items: [
        { 
          id: 'sales',
          title: "Ventas", 
          icon: <FaShoppingCart size={28} />, 
          description: "Consulta y administra ventas", 
          route: "/salesList",
          badge: stats.ventasHoy,
          colorClass: "warning"
        },
        { 
          id: 'fastSales',
          title: "Venta Rápida", 
          icon: <FaShoppingCart size={28} />, 
          description: "Procesa ventas de forma inmediata", 
          route: "/Fastsales",
          colorClass: "info" 
        },
        { 
          id: 'invoicing',
          title: "Facturación", 
          icon: <FaFileInvoice size={28} />, 
          description: "Genera y gestiona facturas", 
          route: "/invoice-list",
          badge: stats.facturasPendientes,
          colorClass: "danger" 
        }
      ]
    },
    {
      id: 'servicesCategory',
      category: "Servicios",
      colorClass: "secondary",
      items: [
        { 
          id: 'labour',
          title: "Mano de Obra", 
          icon: <FaHandshake size={28} />, 
          description: "Gestión de servicios y trabajos", 
          route: "/labour-list",
          colorClass: "secondary" 
        },
        { 
          id: 'assetsManager',
          title: "Administrador de Activos", 
          icon: <FaShoppingCart size={28} />, 
          description: "Gestión de servicios y activos", 
          route: "/assetsManager",
          colorClass: "secondary" 
        },
      ]
    }
  ];

  // Función de logout
  const handleLogout = () => {
    // Limpiar localStorage
    authService.logout();
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    // Opcional: hacer una petición al backend para invalidar el token
    // api.post('/auth/logout/').catch(err => console.log(err));
    
    // Redirigir al login
    navigate('/');
  };

  // Función para obtener iniciales del usuario
  const getUserInitials = () => {
    if (!currentUser) return 'U';
    if (currentUser.first_name && currentUser.last_name) {
      return `${currentUser.first_name[0]}${currentUser.last_name[0]}`.toUpperCase();
    }
    return currentUser.username ? currentUser.username[0].toUpperCase() : 'U';
  };

  // Función para obtener nombre completo
  const getFullName = () => {
    if (!currentUser) return 'Usuario';
    if (currentUser.first_name && currentUser.last_name) {
      return `${currentUser.first_name} ${currentUser.last_name}`;
    }
    console.log(currentUser.first_name, currentUser.last_name);
    return currentUser.username || 'Usuario';
  };

  const getFilteredMenuItems = () => {
    let filtered = menuItems
      .filter(category => homeConfig[category.id] !== false)
      .map(category => ({
        ...category,
        items: category.items.filter(item => homeConfig[item.id] !== false)
      }))
      .filter(category => category.items.length > 0);

    if (categoryOrder.length > 0) {
      filtered = filtered.sort((a, b) => {
        const indexA = categoryOrder.indexOf(a.id);
        const indexB = categoryOrder.indexOf(b.id);
        
        if (indexA !== -1 && indexB !== -1) {
          return indexA - indexB;
        }
        if (indexA !== -1) return -1;
        if (indexB !== -1) return 1;
        return menuItems.findIndex(item => item.id === a.id) - 
               menuItems.findIndex(item => item.id === b.id);
      });
    }

    if (searchTerm) {
      filtered = filtered.map(category => ({
        ...category,
        items: category.items.filter(item => 
          item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.description.toLowerCase().includes(searchTerm.toLowerCase())
        )
      })).filter(category => category.items.length > 0);
    }

    return filtered;
  };

  const filteredMenuItems = getFilteredMenuItems();

  const handleConfigSave = (newConfig, newOrder = []) => {
    setHomeConfig(newConfig);
    if (newOrder.length > 0) {
      setCategoryOrder(newOrder);
    }
  };

  const handleCardClick = (route) => {
    navigate(route);
  };

  return (
    <div className="container-fluid py-4">
      {/* Header con usuario y logout */}
      <div className="row mb-4 align-items-center">
        <div className="col-md-6">
          <Link to="/dashboard" className="text-decoration-none">
            <h1 className="mb-1 text-dark">Dashboard</h1>
          </Link>
          <p className="text-muted">Sistema de Facturación e Inventario</p>
        </div>
        
        <div className="col-md-6 d-flex justify-content-end align-items-center gap-3">
          {/* Barra de búsqueda */}
          {homeConfig.searchBar !== false && (
            <div className="input-group" style={{maxWidth: '300px'}}>
              <span className="input-group-text bg-white">
                <FaSearch />
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Buscar módulo..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          )}

          {/* Notificaciones */}
          <div className="position-relative">
            <button className="btn btn-light rounded-circle p-2 position-relative">
              <FaBell size={18} />
              {stats.facturasPendientes > 0 && (
                <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
                  {stats.facturasPendientes}
                </span>
              )}
            </button>
          </div>

          {/* Menú de usuario */}
          <div className="position-relative">
            <button 
              className="btn btn-light d-flex align-items-center gap-2 px-3"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <div 
                className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center"
                style={{width: '36px', height: '36px', fontSize: '14px', fontWeight: 'bold'}}
              >
                {getUserInitials()}
              </div>
              <div className="text-start d-none d-md-block">
                <div className="small fw-bold">{getFullName()}</div>
                <div className="text-muted" style={{fontSize: '0.75rem'}}>
                  {currentUser?.email || 'usuario@sistema.com'}
                </div>
              </div>
              <FaAngleDown />
            </button>

            {/* Dropdown del usuario */}
            {showUserMenu && (
              <div 
                className="position-absolute end-0 mt-2 bg-white rounded shadow-lg border"
                style={{minWidth: '200px', zIndex: 1000}}
              >
                <div className="p-3 border-bottom">
                  <div className="fw-bold">{getFullName()}</div>
                  <div className="text-muted small">{currentUser?.username}</div>
                </div>
                <div className="py-2">
                  <button 
                    className="btn btn-link text-decoration-none text-dark w-100 text-start px-3 py-2 d-flex align-items-center gap-2"
                    onClick={() => navigate('/profile')}
                  >
                    <FaUser /> Mi Perfil
                  </button>
                  <button 
                    className="btn btn-link text-decoration-none text-dark w-100 text-start px-3 py-2 d-flex align-items-center gap-2"
                    onClick={() => setShowConfig(true)}
                  >
                    <FaCog /> Configuración
                  </button>
                  <hr className="my-1" />
                  <button 
                    className="btn btn-link text-decoration-none text-danger w-100 text-start px-3 py-2 d-flex align-items-center gap-2"
                    onClick={handleLogout}
                  >
                    <FaSignOutAlt /> Cerrar Sesión
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tarjetas de estadísticas */}
      {homeConfig.statsCards !== false && (
        <div className="row mb-4">
          <div className="col-md-3 mb-3">
            <div className="card border-left-primary shadow h-100 py-2">
              <div className="card-body">
                <div className="row no-gutters align-items-center">
                  <div className="col mr-2">
                    <div className="text-xs font-weight-bold text-primary text-uppercase mb-1">
                      Ventas de hoy
                    </div>
                    <div className="h5 mb-0 font-weight-bold text-gray-800">
                      {loading ? '...' : stats.ventasHoy}
                    </div>
                  </div>
                  <div className="col-auto">
                    <div className="bg-light p-3 rounded">
                      <FaShoppingCart className="text-primary" size={24} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div
            className="col-md-3 mb-3"
            style={{ cursor: 'pointer' }}
            onClick={() => navigate('/low-stock-report')}
          >
            <div className="card border-left-danger shadow h-100 py-2">
              <div className="card-body">
                <div className="row no-gutters align-items-center">
                  <div className="col mr-2">
                    <div className="text-xs font-weight-bold text-danger text-uppercase mb-1">
                      Productos bajo stock
                    </div>
                    <div className="h5 mb-0 font-weight-bold text-gray-800">
                      {loading ? '...' : stats.productosBajoStock}
                    </div>
                  </div>
                  <div className="col-auto">
                    <div className="bg-light p-3 rounded">
                      <FaBoxOpen className="text-danger" size={24} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="col-md-3 mb-3">
            <div className="card border-left-warning shadow h-100 py-2">
              <div className="card-body">
                <div className="row no-gutters align-items-center">
                  <div className="col mr-2">
                    <div className="text-xs font-weight-bold text-warning text-uppercase mb-1">
                      Facturas pendientes
                    </div>
                    <div className="h5 mb-0 font-weight-bold text-gray-800">
                      {loading ? '...' : stats.facturasPendientes}
                    </div>
                  </div>
                  <div className="col-auto">
                    <div className="bg-light p-3 rounded">
                      <FaFileInvoice className="text-warning" size={24} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="col-md-3 mb-3">
            <div className="card border-left-success shadow h-100 py-2">
              <div className="card-body">
                <div className="row no-gutters align-items-center">
                  <div className="col mr-2">
                    <div className="text-xs font-weight-bold text-success text-uppercase mb-1">
                      Ingresos mensuales
                    </div>
                    <div className="h5 mb-0 font-weight-bold text-gray-800">
                      ${loading ? '...' : stats.ingresosMensuales}
                    </div>
                  </div>
                  <div className="col-auto">
                    <div className="bg-light p-3 rounded">
                      <FaChartLine className="text-success" size={24} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Módulos por categoría */}
      {filteredMenuItems.map((category, catIndex) => (
        <div key={catIndex} className="mb-4">
          <h2 className="h4 mb-3 pb-2 border-bottom text-uppercase">
            <span className={`text-${category.colorClass}`}>{category.category}</span>
          </h2>
          
          <div className="row">
            {category.items.map((item, itemIndex) => (
              <div key={itemIndex} className="col-md-4 mb-4">
                <div 
                  className="card h-100 shadow-sm cursor-pointer"
                  onClick={() => handleCardClick(item.route)}
                  style={{
                    cursor: 'pointer', 
                    borderLeft: `5px solid var(--bs-${item.colorClass})`,
                    transition: 'transform 0.2s, box-shadow 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-5px)'
                    e.currentTarget.style.boxShadow = '0 0.5rem 1rem rgba(0,0,0,0.15)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '';
                  }}
                >
                  <div className="card-body">
                    <div className="d-flex align-items-center mb-3">
                      <div className={`p-3 rounded bg-light text-${item.colorClass} me-3`}>
                        {item.icon}
                      </div>
                      <h5 className="card-title mb-0">
                        {item.title}
                        {item.badge && (
                          <span className="badge bg-danger ms-2">{item.badge}</span>
                        )}
                      </h5>
                    </div>
                    <p className="card-text text-muted">{item.description}</p>
                    <button className={`btn btn-sm btn-outline-${item.colorClass} mt-2`}>
                      Acceder
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Enlaces rápidos */}
      {homeConfig.quickLinks !== false && (
        <div className="row mt-4 pt-3 border-top">
          <div className="col-12 d-flex justify-content-center flex-wrap gap-3">
            <button onClick={() => handleCardClick('/clients')} className="btn btn-outline-secondary">
              <FaUserFriends className="me-2" />
              <span>Clientes</span>
            </button>
            <button onClick={() => handleCardClick('/reports')} className="btn btn-outline-secondary">
              <FaClipboardList className="me-2" />
              <span>Reportes</span>
            </button>
          </div>
        </div>
      )}

      {/* Modal de configuración */}
      <HomeConfig 
        isOpen={showConfig}
        onClose={() => setShowConfig(false)}
        onSave={handleConfigSave}
      />

      {/* Click fuera del menú para cerrarlo */}
      {showUserMenu && (
        <div 
          className="position-fixed top-0 start-0 w-100 h-100"
          style={{zIndex: 999}}
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </div>
  );
}

export default Home;