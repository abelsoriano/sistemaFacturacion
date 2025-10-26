import React, { useState, useEffect } from 'react';
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
  FaSearch
} from 'react-icons/fa';
import { Link } from "react-router-dom";
import api from '../services/api';
import HomeConfig from '../components/HomeConfig'; // Importa el componente

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
  const navigate = useNavigate();

  // Cargar configuración y orden al iniciar
useEffect(() => {
  const savedConfig = JSON.parse(localStorage.getItem('homeConfig') || '{}');
  const savedOrder = JSON.parse(localStorage.getItem('homeItemOrder') || '[]');
  setHomeConfig(savedConfig);
  setCategoryOrder(savedOrder);
}, []);

// Añade este estado
const [categoryOrder, setCategoryOrder] = useState([]);


  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Obtener la fecha actual para filtrar ventas de hoy
        const today = new Date().toISOString().split('T')[0];
        
        // Obtener datos del dashboard - asegúrate que esta ruta sea correcta
        const dashboardResponse = await api.get('/dashboard/');
        
        // Axios devuelve el objeto completo con la propiedad 'data' que contiene la respuesta JSON
        const dashboardData = dashboardResponse.data;  
        
        // Verificamos que la estructura de datos sea la esperada
        if (!dashboardData || !dashboardData.salesSummary || !dashboardData.inventoryStatus) {
          throw new Error('Datos del dashboard con formato inesperado');
        }
        
        // Intentar obtener facturas pendientes - Omitir si falla
        let facturasPendientes = 0;
        try {
          console.log("Llamando a la API de facturas...");
          const invoicesResponse = await api.get('/invoices/?status=pending');
          const invoicesData = invoicesResponse.data;
          facturasPendientes = Array.isArray(invoicesData) ? invoicesData.length : 0;
        } catch (invoiceErr) {
          console.warn("Error al obtener facturas pendientes:", invoiceErr);
        }
        
        // Calcular ventas de hoy de forma segura
        let todaySales = 0;
        if (dashboardData.recentSales && Array.isArray(dashboardData.recentSales)) {
          todaySales = dashboardData.recentSales.filter(sale => 
            sale.date && sale.date.startsWith && sale.date.startsWith(today)
          ).length;
        }
        
        // Calcular productos bajo stock de forma segura
        let productosBajoStock = 0;
        if (dashboardData.inventoryStatus && 
            typeof dashboardData.inventoryStatus.low_stock_count === 'number') {
          productosBajoStock = dashboardData.inventoryStatus.low_stock_count;
        }
        
        // Calcular ingresos mensuales de forma segura
        let ingresosMensuales = "0";
        if (dashboardData.salesSummary && 
            (typeof dashboardData.salesSummary.total_sales === 'number' || 
             typeof dashboardData.salesSummary.total_sales === 'string')) {
          const totalSales = parseFloat(dashboardData.salesSummary.total_sales) || 0;
          ingresosMensuales = new Intl.NumberFormat('es-MX').format(totalSales);
        }
        
        // Actualizar estadísticas con datos reales
        const newStats = {
          ventasHoy: todaySales,
          productosBajoStock: productosBajoStock,
          facturasPendientes: facturasPendientes,
          ingresosMensuales: ingresosMensuales
        };
        
        console.log("Nuevas estadísticas:", newStats);
        setStats(newStats);
        setLoading(false);
      } catch (err) {
        console.error("Error al cargar datos:", err);
        setError(err.message);
        setLoading(false);
        
        // Si hay error, mostrar valores por defecto
        setStats({
          ventasHoy: 0,
          productosBajoStock: 0,
          facturasPendientes: 0,
          ingresosMensuales: "0"
        });
      }
    };

    fetchDashboardData();
  }, [setError]); // está bien incluir setError (setter proviene de useState)

   const menuItems = [
    {
    id: 'inventoryCategory', // ← Añade este ID
    category: "Inventario",
    colorClass: "primary",
    items: [
      { 
        id: 'products', // ← Añade este ID
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
        }
      ]
    }
  ];

  

  

  // Mejora la función getFilteredMenuItems para usar el ordenamiento
const getFilteredMenuItems = () => {
  // Primero aplicar filtro de configuración
  let filtered = menuItems
    .filter(category => homeConfig[category.id] !== false)
    .map(category => ({
      ...category,
      items: category.items.filter(item => homeConfig[item.id] !== false)
    }))
    .filter(category => category.items.length > 0);

  // Aplicar ordenamiento personalizado si existe
  if (categoryOrder.length > 0) {
    filtered = filtered.sort((a, b) => {
      const indexA = categoryOrder.indexOf(a.id);
      const indexB = categoryOrder.indexOf(b.id);
      
      // Si ambos están en el orden personalizado, ordenar por ese orden
      if (indexA !== -1 && indexB !== -1) {
        return indexA - indexB;
      }
      // Si solo A está en el orden, A va primero
      if (indexA !== -1) return -1;
      // Si solo B está en el orden, B va primero
      if (indexB !== -1) return 1;
      // Si ninguno está en el orden, mantener orden original
      return menuItems.findIndex(item => item.id === a.id) - 
             menuItems.findIndex(item => item.id === b.id);
    });
  }



  // Luego aplicar filtro de búsqueda si existe
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
// Función para manejar clics en tarjetas
const handleCardClick = (route) => {
  console.log(`Navegando a: ${route}`);
  // Aquí iría la lógica de navegación real
  window.location.href = route;
};

return (
  <div className="container-fluid py-4">
    {/* Encabezado y barra de búsqueda */}
    {homeConfig.searchBar !== false && (
      <div className="row mb-4 align-items-center">
        <div className="col-md-6">
          <Link to="/" className="no-underline">
            <h1 className="mb-1 text-black">Dashboard</h1>
          </Link>
          <p className="text-muted">Sistema de Facturación e Inventario</p>
        </div>
        <div className="col-md-6">
          <div className="input-group">
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
        </div>
      </div>
    )}

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
                className={`card h-100 shadow-sm border-left-5 cursor-pointer border-hover-${item.colorClass}`} 
                onClick={() => handleCardClick(item.route)}
                style={{cursor: 'pointer', borderLeft: `5px solid var(--bs-${item.colorClass})`}}
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
          <button onClick={() => setShowConfig(true)} className="btn btn-outline-secondary">
            <FaCog className="me-2" />
            <span>Configuración</span>
          </button>
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
  </div>
);
}

export default Home;
