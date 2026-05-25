import React, { useState, useEffect } from 'react';
import { authService } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { ROUTE_PERMISSIONS, SALE_TOTALS_PERMISSION, userHasPermissions } from '../utils/permissions';
import '../css/Home.css';
import {
  IconSearch,
  IconBell,
  IconChevron,
  IconUser,
  IconCog,
  IconLogout,
  IconCart,
  IconAlert,
  IconFile,
  IconChart,
  IconBox,
  IconTag,
  IconWarehouse,
  IconBolt,
  IconInvoice,
  IconTools,
  IconBuilding,
  IconUsers,
  IconReport,
  IconDashboard,
} from './Icons';

function Home() {
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState({ ventasHoy: 0, productosBajoStock: 0, facturasPendientes: 0, ingresosMensuales: '0' });
  const [loading, setLoading] = useState(true);
  const [categoryOrder, setCategoryOrder] = useState([]);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [readNotifications, setReadNotifications] = useState(() => JSON.parse(localStorage.getItem('readNotifications') || '[]'));
  const [currentUser, setCurrentUser] = useState(() => JSON.parse(localStorage.getItem('user') || '{}'));
  const navigate = useNavigate();
  
  const canViewSalesTotals = userHasPermissions(currentUser, [SALE_TOTALS_PERMISSION]);

  const today = new Date().toLocaleDateString('es-MX', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  useEffect(() => {
    setCurrentUser(JSON.parse(localStorage.getItem('user') || '{}'));
  }, []);

  useEffect(() => {
    const savedOrder = JSON.parse(localStorage.getItem('homeItemOrder') || '[]');
    setCategoryOrder(savedOrder);
  }, []);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const user = currentUser || {};
        const todayStr = new Date().toISOString().split('T')[0];
        let dashboardData = {};

        if (userHasPermissions(user, ROUTE_PERMISSIONS['/dashboard'])) {
          const dashboardResponse = await api.get('/dashboard/');
          dashboardData = dashboardResponse.data;

          if (!dashboardData?.salesSummary || !dashboardData?.inventoryStatus) {
            throw new Error('Datos del dashboard con formato inesperado');
          }
        }

        let facturasPendientes = 0;
        try {
          const invoicesResponse = await api.get('/invoices/?status=pending');
          const invoicesData = invoicesResponse.data;
          facturasPendientes = Array.isArray(invoicesData) ? invoicesData.length : 0;
        } catch (e) {}

        let todaySales = 0;
        if (Array.isArray(dashboardData.recentSales)) {
          todaySales = dashboardData.recentSales.filter(s => s.date?.startsWith(todayStr)).length;
        }

        const productosBajoStock = typeof dashboardData.inventoryStatus?.low_stock_count === 'number'
          ? dashboardData.inventoryStatus.low_stock_count : 0;

        const totalSales = canViewSalesTotals ? (parseFloat(dashboardData.salesSummary?.total_sales) || 0) : 0;
        const ingresosMensuales = new Intl.NumberFormat('es-MX').format(totalSales);

        setStats({ ventasHoy: todaySales, productosBajoStock, facturasPendientes, ingresosMensuales });
      } catch (err) {
        console.error('Error al cargar datos:', err);
        setStats({ ventasHoy: 0, productosBajoStock: 0, facturasPendientes: 0, ingresosMensuales: '0' });
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, [currentUser, canViewSalesTotals]);

  // ── Notificaciones: cargar solo cuando se abre el panel ──
  const fetchNotifications = async () => {
    try {
      const invoicesResponse = await api.get('/invoices/?status=pending');
      const inv = Array.isArray(invoicesResponse.data) ? invoicesResponse.data : [];
      // Map to notification shape
      const invNotifs = inv.map(i => ({ id: `invoice-${i.id}`, type: 'invoice', title: `Factura pendiente #${i.id}`, subtitle: i.client_name || i.client || '', meta: i }));
      // Add a low-stock summary notification
      const lowStockNotif = { id: 'low-stock', type: 'low_stock', title: `Productos bajo stock: ${stats.productosBajoStock || 0}`, subtitle: 'Revisa el reporte de bajo stock', meta: null };
      setNotifications([lowStockNotif, ...invNotifs]);
    } catch (err) {
      console.error('Error cargando notificaciones:', err);
    }
  };

  useEffect(() => {
    // persist read notifications
    localStorage.setItem('readNotifications', JSON.stringify(readNotifications || []));
  }, [readNotifications]);

  const openNotifications = async () => {
    setShowNotifications(v => !v);
    if (!showNotifications) {
      await fetchNotifications();
    }
  };

  const markAsRead = (notifId) => {
    if (!readNotifications.includes(notifId)) setReadNotifications(prev => [...prev, notifId]);
  };

  const markAllRead = () => setReadNotifications(notifs => {
    const ids = (notifications || []).map(n => n.id);
    const merged = Array.from(new Set([...(notifs || []), ...ids]));
    return merged;
  });

  const unreadCount = (notifications || []).filter(n => !readNotifications.includes(n.id)).length;

  const menuItems = [
    {
      id: 'inventoryCategory', category: 'Inventario',
      items: [
        { id: 'products',    title: 'Productos',   icon: <IconBox />,       desc: 'Gestiona el catálogo de productos',     route: '/productsList',  color: 'teal'   },
        { id: 'categories',  title: 'Categorías',  icon: <IconTag />,       desc: 'Administra categorías de productos',    route: '/categoriaList', color: 'purple' },
        { id: 'warehouse',   title: 'Almacén',     icon: <IconWarehouse />, desc: 'Control de inventario y stock',         route: '/list-item',     color: 'gray'   },
      ]
    },
    {
      id: 'salesCategory', category: 'Ventas',
      items: [
        { id: 'sales',      title: 'Ventas',        icon: <IconCart />,    desc: 'Consulta y administra ventas',         route: '/salesList',    color: 'amber', badge: stats.ventasHoy },
        { id: 'fastSales',  title: 'Venta rápida',  icon: <IconBolt />,    desc: 'Procesa ventas de forma inmediata',    route: '/Fastsales',    color: 'teal'  },
        { id: 'invoicing',  title: 'Facturación',   icon: <IconInvoice />, desc: 'Genera y gestiona facturas',           route: '/invoice-list', color: 'coral', badge: stats.facturasPendientes },
      ]
    },
    {
      id: 'servicesCategory', category: 'Servicios',
      items: [
        { id: 'labour',        title: 'Mano de obra', icon: <IconTools />,    desc: 'Gestión de servicios y trabajos', route: '/labour-list',    color: 'blue' },
        { id: 'assetsManager', title: 'Activos',      icon: <IconBuilding />, desc: 'Gestión de servicios y activos',  route: '/assetsManager',  color: 'gray' },
      ]
    },
    {
      id: 'adminCategory', category: 'Administración',
      items: [
        { id: 'pdfConfig', title: 'Configuración de ticket', icon: <IconCog />, desc: 'Edita datos de la empresa y el footer del PDF', route: '/pdf-config', color: 'blue' },
        { id: 'users',  title: 'Usuarios',  icon: <IconUsers />, desc: 'Gestiona usuarios del sistema', route: '/users',  color: 'red' },
        { id: 'groups', title: 'Grupos',    icon: <IconUsers />, desc: 'Administra roles y permisos',   route: '/groups', color: 'orange' },
      ]
    },
  ];

  const handleLogout = () => {
    authService.logout();
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  const getUserInitials = () => {
    if (!currentUser) return 'U';
    if (currentUser.first_name && currentUser.last_name)
      return `${currentUser.first_name[0]}${currentUser.last_name[0]}`.toUpperCase();
    return currentUser.username?.[0]?.toUpperCase() || 'U';
  };

  const getFullName = () => {
    if (!currentUser) return 'Usuario';
    if (currentUser.first_name && currentUser.last_name)
      return `${currentUser.first_name} ${currentUser.last_name}`;
    return currentUser.username || 'Usuario';
  };

  const getGreeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Buenos días';
    if (h < 19) return 'Buenas tardes';
    return 'Buenas noches';
  };

  const getFilteredMenuItems = () => {
    let filtered = menuItems
      .map(cat => ({
        ...cat,
        items: cat.items.filter(item => (
          userHasPermissions(currentUser, ROUTE_PERMISSIONS[item.route] || [])
        ))
      }))
      .filter(cat => cat.items.length > 0);

    if (categoryOrder.length > 0) {
      filtered = filtered.sort((a, b) => {
        const ia = categoryOrder.indexOf(a.id);
        const ib = categoryOrder.indexOf(b.id);
        if (ia !== -1 && ib !== -1) return ia - ib;
        if (ia !== -1) return -1;
        if (ib !== -1) return 1;
        return menuItems.findIndex(x => x.id === a.id) - menuItems.findIndex(x => x.id === b.id);
      });
    }

    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      filtered = filtered
        .map(cat => ({ ...cat, items: cat.items.filter(item => item.title.toLowerCase().includes(q) || item.desc.toLowerCase().includes(q)) }))
        .filter(cat => cat.items.length > 0);
    }

    return filtered;
  };


  const canOpen = (route) => userHasPermissions(currentUser, ROUTE_PERMISSIONS[route] || []);

  const filteredMenuItems = getFilteredMenuItems();

  return (
    <>
    
      <div className="hd-shell">

        {/* Navbar */}
        <nav className="hd-nav">
          <Link to="/home" className="hd-nav-brand">
          <img src="/logo.png" alt="Logo" className="hd-logo" />
            Sistema <span>Facturación</span>
          </Link>

            <div className="hd-nav-search">
              <IconSearch />
              <input
                type="text"
                placeholder="Buscar módulo..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
              />
            </div>

          {/* Notificaciones */}
          <div style={{ position: 'relative' }}>
            <button className="hd-bell-btn" aria-label="Notificaciones" onClick={openNotifications}>
              <IconBell />
              {(unreadCount || stats.facturasPendientes > 0) && <div className="hd-bell-dot" />}
            </button>

            {showNotifications && (
              <div className="hd-notif-dropdown" style={{ position: 'absolute', right: 0, top: '40px', width: 340, background: '#fff', boxShadow: '0 8px 24px rgba(0,0,0,0.12)', borderRadius: 8, zIndex: 200 }}>
                <div style={{ padding: '10px 12px', borderBottom: '1px solid #f3f4f6', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>Notificaciones</strong>
                  <button style={{ background: 'transparent', border: 'none', color: '#6b7280', cursor: 'pointer' }} onClick={markAllRead}>Marcar todo leído</button>
                </div>
                <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                  {(notifications || []).length === 0 ? (
                    <div style={{ padding: 14, color: '#6b7280' }}>Sin notificaciones</div>
                  ) : (
                    notifications.map(n => (
                      <div key={n.id} onClick={() => {
                        // acciones por tipo
                        if (n.type === 'invoice') {
                          navigate(`/invoices/${n.meta.id}`);
                          markAsRead(n.id);
                        } else if (n.type === 'low_stock') {
                          navigate('/low-stock-report');
                          markAsRead(n.id);
                        }
                        setShowNotifications(false);
                      }}
                        style={{ padding: 12, borderBottom: '1px solid #f7f7f8', cursor: 'pointer', background: readNotifications.includes(n.id) ? '#fbfdfb' : '#fff' }}>
                        <div style={{ fontWeight: 600 }}>{n.title}</div>
                        {n.subtitle && <div style={{ fontSize: 12, color: '#9ca3af' }}>{n.subtitle}</div>}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Usuario */}
          <div style={{ position: 'relative' }}>
            <button className="hd-user-btn" onClick={() => setShowUserMenu(v => !v)}>
              <div className="hd-avatar">{getUserInitials()}</div>
              <div className="hd-user-info">
                <div className="hd-user-name">{getFullName()}</div>
                <div className="hd-user-role">{currentUser?.email || 'usuario@sistema.com'}</div>
              </div>
              <IconChevron />
            </button>

            {showUserMenu && (
              <div className="hd-dropdown">
                <div className="hd-dropdown-header">
                  <p>{getFullName()}</p>
                  <p>{currentUser?.username}</p>
                </div>
                <button className="hd-dropdown-item" onClick={() => { navigate('/profile'); setShowUserMenu(false); }}>
                  <IconUser /> Mi perfil
                </button>
                <div className="hd-dropdown-divider" />
                <button className="hd-dropdown-item danger" onClick={handleLogout}>
                  <IconLogout /> Cerrar sesión
                </button>
              </div>
            )}
          </div>
        </nav>

        {/* Body */}
        <div className="hd-body">

          {/* Saludo */}
          <div className="hd-greeting">
            <div>
              <div className="hd-greeting-main">{getGreeting()}, {getFullName().split(' ')[0]}</div>
              <div className="hd-greeting-sub">Aquí está el resumen de hoy</div>
            </div>
            <div className="hd-greeting-date">{today}</div>
          </div>

          {/* Stats */}
            <div className="hd-stats">
              <div className="hd-stat">
                <div className="hd-stat-label" style={{ color: '#1D9E75' }}>
                  <IconCart /> Ventas hoy
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">{stats.ventasHoy}</div>}
                <div className="hd-stat-sub">transacciones</div>
              </div>

              {canOpen('/low-stock-report') && (
              <div className="hd-stat clickable" onClick={() => navigate('/low-stock-report')}>
                <div className="hd-stat-label" style={{ color: '#E24B4A' }}>
                  <IconAlert /> Bajo stock
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">{stats.productosBajoStock}</div>}
                <div className="hd-stat-sub">productos · ver reporte →</div>
              </div>
              )}

              <div className="hd-stat">
                <div className="hd-stat-label" style={{ color: '#BA7517' }}>
                  <IconFile /> Facturas
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">{stats.facturasPendientes}</div>}
                <div className="hd-stat-sub">pendientes</div>
              </div>

              {canViewSalesTotals && (
              <div className="hd-stat">
                <div className="hd-stat-label" style={{ color: '#378ADD' }}>
                  <IconChart /> Ingresos
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">${stats.ingresosMensuales}</div>}
                <div className="hd-stat-sub">este mes</div>
              </div>
              )}
            </div>

          {/* Módulos por categoría */}
          {filteredMenuItems.map(category => (
            <div key={category.id}>
              <div className="hd-section">{category.category}</div>
              <div className={`hd-modules${category.items.length === 2 ? ' two-col' : ''}`}>
                {category.items.map(item => (
                  <div key={item.id} className="hd-module" onClick={() => navigate(item.route)}>
                    <div className="hd-module-top">
                      <div className={`hd-module-icon ${item.color}`}>{item.icon}</div>
                      {item.badge > 0 && (
                        <span className="hd-module-badge">{item.badge}</span>
                      )}
                    </div>
                    <div className="hd-module-name">{item.title}</div>
                    <div className="hd-module-desc">{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Accesos directos */}
          
            <div>
              <div className="hd-section">Accesos directos</div>
              <div className="hd-quicklinks">
                {canOpen('/clients') && <button className="hd-ql" onClick={() => navigate('/clients')}>
                  <IconUsers /> Clientes
                </button>}
                {canOpen('/sales-reports') && <button className="hd-ql" onClick={() => navigate('/sales-reports')}>
                  <IconReport /> Reportes
                </button>}
                {canOpen('/dashboard') && <button className="hd-ql" onClick={() => navigate('/dashboard')}>
                  <IconDashboard /> Dashboard
                </button>}
              </div>
            </div>
      
        </div>

        {/* Overlay para cerrar menú de usuario */}
        {showUserMenu && (
          <div
            style={{ position: 'fixed', inset: 0 }}
            onClick={() => setShowUserMenu(false)}
          />
        )}
      </div>
    </>
  );
}

export default Home;
