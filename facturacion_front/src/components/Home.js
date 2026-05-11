import React, { useState, useEffect } from 'react';
import { authService } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import api from '../services/api';
import HomeConfig from '../components/HomeConfig';

const styles = `
  .hd-shell { background: #f4f5f7; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

  /* Navbar */
  .hd-nav {
    background: #fff;
    border-bottom: 0.5px solid #e5e7eb;
    padding: 0 24px;
    height: 56px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .hd-nav-brand { font-size: 15px; font-weight: 600; color: #111827; flex: 1; text-decoration: none; }
  .hd-nav-brand span { color: #1D9E75; }
  .hd-nav-search {
    display: flex; align-items: center; gap: 7px;
    background: #f9fafb; border: 0.5px solid #e5e7eb;
    border-radius: 8px; padding: 7px 12px; width: 220px;
    transition: border-color 0.15s;
  }
  .hd-nav-search:focus-within { border-color: #1D9E75; background: #fff; }
  .hd-nav-search input { border: none; background: transparent; font-size: 13px; color: #111827; outline: none; width: 100%; }
  .hd-nav-search svg { color: #9ca3af; flex-shrink: 0; }
  .hd-bell-btn {
    width: 34px; height: 34px; border-radius: 50%;
    background: #f9fafb; border: 0.5px solid #e5e7eb;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; position: relative; transition: background 0.15s;
  }
  .hd-bell-btn:hover { background: #f3f4f6; }
  .hd-bell-dot {
    position: absolute; top: 5px; right: 5px;
    width: 8px; height: 8px; background: #E24B4A;
    border-radius: 50%; border: 1.5px solid #fff;
  }
  .hd-user-btn {
    display: flex; align-items: center; gap: 8px;
    background: transparent; border: 0.5px solid #e5e7eb;
    border-radius: 8px; padding: 5px 10px;
    cursor: pointer; transition: background 0.15s;
  }
  .hd-user-btn:hover { background: #f9fafb; }
  .hd-avatar {
    width: 30px; height: 30px; border-radius: 50%;
    background: #E1F5EE; display: flex; align-items: center;
    justify-content: center; font-size: 11px; font-weight: 600; color: #085041;
    flex-shrink: 0;
  }
  .hd-user-info { text-align: left; }
  .hd-user-name { font-size: 12px; font-weight: 600; color: #111827; line-height: 1.2; }
  .hd-user-role { font-size: 10px; color: #9ca3af; }

  /* Dropdown usuario */
  .hd-dropdown {
    position: absolute; top: calc(100% + 6px); right: 0;
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    min-width: 200px; z-index: 200; overflow: hidden;
  }
  .hd-dropdown-header { padding: 12px 14px; border-bottom: 0.5px solid #f3f4f6; }
  .hd-dropdown-header p:first-child { font-size: 13px; font-weight: 600; color: #111827; }
  .hd-dropdown-header p:last-child { font-size: 11px; color: #9ca3af; margin-top: 1px; }
  .hd-dropdown-item {
    display: flex; align-items: center; gap: 9px;
    padding: 9px 14px; font-size: 13px; color: #374151;
    cursor: pointer; background: transparent; border: none;
    width: 100%; text-align: left; transition: background 0.1s;
  }
  .hd-dropdown-item:hover { background: #f9fafb; }
  .hd-dropdown-item.danger { color: #991b1b; }
  .hd-dropdown-item.danger:hover { background: #fef2f2; }
  .hd-dropdown-divider { height: 0.5px; background: #f3f4f6; margin: 4px 0; }

  /* Body */
  .hd-body { max-width: 1100px; margin: 0 auto; padding: 24px 24px 40px; display: flex; flex-direction: column; gap: 24px; }

  /* Greeting */
  .hd-greeting { display: flex; justify-content: space-between; align-items: flex-end; }
  .hd-greeting-main { font-size: 20px; font-weight: 600; color: #111827; }
  .hd-greeting-sub { font-size: 13px; color: #6b7280; margin-top: 3px; }
  .hd-greeting-date { font-size: 12px; color: #9ca3af; text-align: right; }

  /* Stats */
  .hd-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
  .hd-stat {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; padding: 14px 16px; cursor: default;
    transition: border-color 0.15s;
  }
  .hd-stat.clickable { cursor: pointer; }
  .hd-stat.clickable:hover { border-color: #9ca3af; }
  .hd-stat-label {
    display: flex; align-items: center; gap: 5px;
    font-size: 10px; font-weight: 600; color: #9ca3af;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
  }
  .hd-stat-val { font-size: 22px; font-weight: 600; color: #111827; }
  .hd-stat-sub { font-size: 11px; color: #9ca3af; margin-top: 3px; }
  .hd-stat-loading { font-size: 22px; color: #d1d5db; }

  /* Section header */
  .hd-section {
    display: flex; align-items: center; gap: 10px;
    font-size: 10px; font-weight: 600; color: #9ca3af;
    text-transform: uppercase; letter-spacing: 0.07em;
    margin-bottom: 10px;
  }
  .hd-section::after { content: ''; flex: 1; height: 0.5px; background: #f3f4f6; }

  /* Module grid */
  .hd-modules { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .hd-modules.two-col { grid-template-columns: repeat(2, 1fr); }
  .hd-module {
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 10px; padding: 14px 16px; cursor: pointer;
    display: flex; flex-direction: column; gap: 8px;
    transition: border-color 0.15s, transform 0.1s;
  }
  .hd-module:hover { border-color: #9ca3af; transform: translateY(-1px); }
  .hd-module-top { display: flex; align-items: center; justify-content: space-between; }
  .hd-module-icon {
    width: 36px; height: 36px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  }
  .hd-module-icon.teal   { background: #E1F5EE; color: #0F6E56; }
  .hd-module-icon.purple { background: #EEEDFE; color: #534AB7; }
  .hd-module-icon.gray   { background: #F1EFE8; color: #5F5E5A; }
  .hd-module-icon.amber  { background: #FAEEDA; color: #854F0B; }
  .hd-module-icon.coral  { background: #FAECE7; color: #993C1D; }
  .hd-module-icon.blue   { background: #E6F1FB; color: #185FA5; }
  .hd-module-name { font-size: 13px; font-weight: 600; color: #111827; }
  .hd-module-desc { font-size: 11px; color: #9ca3af; line-height: 1.4; }
  .hd-module-badge {
    background: #FCEBEB; color: #A32D2D; font-size: 10px;
    padding: 2px 8px; border-radius: 10px; font-weight: 500; flex-shrink: 0;
  }

  /* Quick links */
  .hd-quicklinks { display: flex; gap: 8px; flex-wrap: wrap; }
  .hd-ql {
    display: flex; align-items: center; gap: 6px;
    background: #fff; border: 0.5px solid #e5e7eb;
    border-radius: 8px; padding: 7px 14px; font-size: 12px;
    color: #6b7280; cursor: pointer; transition: all 0.12s;
  }
  .hd-ql:hover { color: #111827; border-color: #9ca3af; background: #f9fafb; }

  @media (max-width: 768px) {
    .hd-stats { grid-template-columns: repeat(2, 1fr); }
    .hd-modules { grid-template-columns: repeat(2, 1fr); }
    .hd-modules.two-col { grid-template-columns: 1fr; }
    .hd-nav-search { display: none; }
    .hd-user-info { display: none; }
  }
`;

// Iconos SVG inline livianos
const IconSearch = () => (
  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);
const IconBell = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
);
const IconChevron = () => (
  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);
const IconUser = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
  </svg>
);
const IconCog = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
  </svg>
);
const IconLogout = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
);
const IconCart = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
  </svg>
);
const IconAlert = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);
const IconFile = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
  </svg>
);
const IconChart = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
  </svg>
);
const IconBox = () => (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
  </svg>
);
const IconTag = () => (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
    <line x1="7" y1="7" x2="7.01" y2="7"/>
  </svg>
);
const IconWarehouse = () => (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);
const IconBolt = () => (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
  </svg>
);
const IconInvoice = () => (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1z"/>
    <line x1="9" y1="7" x2="15" y2="7"/><line x1="9" y1="11" x2="15" y2="11"/>
  </svg>
);
const IconTools = () => (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
  </svg>
);
const IconBuilding = () => (
  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
  </svg>
);
const IconUsers = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);
const IconReport = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
  </svg>
);
const IconDashboard = () => (
  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
  </svg>
);

function Home() {
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState({ ventasHoy: 0, productosBajoStock: 0, facturasPendientes: 0, ingresosMensuales: '0' });
  const [loading, setLoading] = useState(true);
  const [showConfig, setShowConfig] = useState(false);
  const [homeConfig, setHomeConfig] = useState({});
  const [categoryOrder, setCategoryOrder] = useState([]);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const navigate = useNavigate();

  const today = new Date().toLocaleDateString('es-MX', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setCurrentUser(user);
  }, []);

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
        const todayStr = new Date().toISOString().split('T')[0];
        const dashboardResponse = await api.get('/dashboard/');
        const dashboardData = dashboardResponse.data;

        if (!dashboardData?.salesSummary || !dashboardData?.inventoryStatus) {
          throw new Error('Datos del dashboard con formato inesperado');
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

        const productosBajoStock = typeof dashboardData.inventoryStatus.low_stock_count === 'number'
          ? dashboardData.inventoryStatus.low_stock_count : 0;

        const totalSales = parseFloat(dashboardData.salesSummary?.total_sales) || 0;
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
  }, []);

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
      .filter(cat => homeConfig[cat.id] !== false)
      .map(cat => ({ ...cat, items: cat.items.filter(item => homeConfig[item.id] !== false) }))
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

  const handleConfigSave = (newConfig, newOrder = []) => {
    setHomeConfig(newConfig);
    if (newOrder.length > 0) setCategoryOrder(newOrder);
  };

  const filteredMenuItems = getFilteredMenuItems();

  return (
    <>
      <style>{styles}</style>
      <div className="hd-shell">

        {/* Navbar */}
        <nav className="hd-nav">
          <Link to="/dashboard" className="hd-nav-brand">
            Sistema <span>Facturación</span>
          </Link>

          {homeConfig.searchBar !== false && (
            <div className="hd-nav-search">
              <IconSearch />
              <input
                type="text"
                placeholder="Buscar módulo..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
              />
            </div>
          )}

          {/* Notificaciones */}
          <button className="hd-bell-btn" aria-label="Notificaciones">
            <IconBell />
            {stats.facturasPendientes > 0 && <div className="hd-bell-dot" />}
          </button>

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
                <button className="hd-dropdown-item" onClick={() => { setShowConfig(true); setShowUserMenu(false); }}>
                  <IconCog /> Configuración
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
          {homeConfig.statsCards !== false && (
            <div className="hd-stats">
              <div className="hd-stat">
                <div className="hd-stat-label" style={{ color: '#1D9E75' }}>
                  <IconCart /> Ventas hoy
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">{stats.ventasHoy}</div>}
                <div className="hd-stat-sub">transacciones</div>
              </div>

              <div className="hd-stat clickable" onClick={() => navigate('/low-stock-report')}>
                <div className="hd-stat-label" style={{ color: '#E24B4A' }}>
                  <IconAlert /> Bajo stock
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">{stats.productosBajoStock}</div>}
                <div className="hd-stat-sub">productos · ver reporte →</div>
              </div>

              <div className="hd-stat">
                <div className="hd-stat-label" style={{ color: '#BA7517' }}>
                  <IconFile /> Facturas
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">{stats.facturasPendientes}</div>}
                <div className="hd-stat-sub">pendientes</div>
              </div>

              <div className="hd-stat">
                <div className="hd-stat-label" style={{ color: '#378ADD' }}>
                  <IconChart /> Ingresos
                </div>
                {loading ? <div className="hd-stat-loading">—</div> : <div className="hd-stat-val">${stats.ingresosMensuales}</div>}
                <div className="hd-stat-sub">este mes</div>
              </div>
            </div>
          )}

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
          {homeConfig.quickLinks !== false && (
            <div>
              <div className="hd-section">Accesos directos</div>
              <div className="hd-quicklinks">
                <button className="hd-ql" onClick={() => navigate('/clients')}>
                  <IconUsers /> Clientes
                </button>
                <button className="hd-ql" onClick={() => navigate('/reports')}>
                  <IconReport /> Reportes
                </button>
                <button className="hd-ql" onClick={() => navigate('/dashboard')}>
                  <IconDashboard /> Dashboard
                </button>
                <button className="hd-ql" onClick={() => setShowConfig(true)}>
                  <IconCog /> Configuración
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Modal configuración */}
        <HomeConfig
          isOpen={showConfig}
          onClose={() => setShowConfig(false)}
          onSave={handleConfigSave}
        />

        {/* Overlay para cerrar menú de usuario */}
        {showUserMenu && (
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 150 }}
            onClick={() => setShowUserMenu(false)}
          />
        )}
      </div>
    </>
  );
}

export default Home;