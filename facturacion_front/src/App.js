import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import { ROUTE_PERMISSIONS } from './utils/permissions';

import Home from './components/Home';
import CategoryForm from './components/CategoryForm';
import ProductForm from './components/ProductForm';
import ProductList from './components/ProductList';
import  CategoryList from './components/CategoryList';
import  SalesForm from './components/SalesForm';
import  SalesList from './components/SalesList';
import InvoiceForm from "./components/InvoiceForm";
import ProductHistory from './components/ProductHistory';

import FastSalesForm from "./components/FastSalesForm";
import AlmacenForm from "./components/AlmacenForm";
import AlmacenList from "./components/AlmacenList";
import LabourForm from "./components/LabourForm";
import LabourList from "./components/LabourList";
import SalesPDFReport from './components/SalesPDFReport';
import Dashboard from './components/Dashboard';
import InvoiceList from'./components/InvoiceList';
import InvoiceDetail from'./components/InvoiceDetail';
import LowStockProducts from './components/LowStockProducts'
import AssetsManager from './components/AssetsManager'
import AssetForm from './components/AssetForm'
import Login from './components/Login'
import Profile from './components/Profile';
import ClientList from './components/ClientList';
import ClientForm from './components/ClientForm';
import UserList from './components/UserList';
import UserForm from './components/UserForm';
import GroupList from './components/GroupList';
import GroupForm from './components/GroupForm';
import PDFConfig from './components/PDFConfig';


/**
 * Componente para rutas públicas (solo Login)
 * Si ya está autenticado, redirige al home
 */
function PublicRoute({ children }) {
  const token = localStorage.getItem('token');
  
  if (token) {
    return <Navigate to="/home" replace />;
  }
  
  return children;
}


function App() {
  const protect = (component, permissions = []) => (
    <ProtectedRoute permissions={permissions}>{component}</ProtectedRoute>
  );

  return (
    <Router>
      <Routes>

        {/* ============================================ */}
        {/* RUTAS PÚBLICAS - No requieren autenticación  */}
        {/* ============================================ */}
        <Route path="/" element={<PublicRoute> <Login /> </PublicRoute>} />
        <Route path="/profile" element={protect(<Profile />)} />
        
        <Route path="/dashboard" element={protect(<Dashboard />, ROUTE_PERMISSIONS['/dashboard'])}/>
        <Route path="/home" element={protect(<Home/>)} />

        <Route path="/categoriesForm" element={protect(<CategoryForm />, ROUTE_PERMISSIONS['/categoriesForm'])} />
        <Route path="/categoriaList" element={protect(<CategoryList />, ROUTE_PERMISSIONS['/categoriaList'])} />
        <Route path="/categoriesForm/:id"  element={protect(<CategoryForm />, ['facturacion.change_category'])} /> {/* Para editar */}

        <Route path="/productsList" element={protect(<ProductList />, ROUTE_PERMISSIONS['/productsList'])} />
        <Route path="/productsForm" element={protect(<ProductForm />, ROUTE_PERMISSIONS['/productsForm'])} />
        <Route path="/productsForm/:id" element={protect(<ProductForm />, ['facturacion.change_product'])} /> {/* Para editar */}
        <Route path="/products/:id/history" element={protect(<ProductHistory />, ['facturacion.view_product'])} />

        <Route path="/sales" element={protect(<SalesForm />, ROUTE_PERMISSIONS['/sales'])} />
        <Route path="/Fastsales" element={protect(<FastSalesForm />, ROUTE_PERMISSIONS['/Fastsales'])} />
        <Route path="/salesList" element={protect(<SalesList />, ROUTE_PERMISSIONS['/salesList'])} />
        <Route path="/Fastsales/:id" element={protect(<SalesForm />, ['facturacion.change_sale'])} />
        
        <Route path="/create-invoice" element={protect(<InvoiceForm />, ROUTE_PERMISSIONS['/create-invoice'])} />
        <Route path="/invoice-list" element={protect(<InvoiceList />, ROUTE_PERMISSIONS['/invoice-list'])} />
         <Route path="/invoices/:id" element={protect(<InvoiceDetail />, ['facturacion.view_invoice'])} />

        <Route path="/register-item" element={protect(<AlmacenForm />, ROUTE_PERMISSIONS['/register-item'])} />
        <Route path="/list-item" element={protect(<AlmacenList />, ROUTE_PERMISSIONS['/list-item'])} />
        <Route path="/register-item/:id" element={protect(<AlmacenForm />, ['facturacion.change_almacen'])} /> {/* Para editar */}

        <Route path="/register-labour" element={protect(<LabourForm />, ROUTE_PERMISSIONS['/register-labour'])} />
        <Route path="/labour-list" element={protect(<LabourList />, ROUTE_PERMISSIONS['/labour-list'])} />
        <Route path="/register-labour/:id" element={protect(<LabourForm />, ['facturacion.change_labour'])} /> {/* Para editar */}

        <Route path="/sales-reports" element={protect(<SalesPDFReport />, ROUTE_PERMISSIONS['/sales-reports'])} />


        <Route path="/low-stock-report" element={protect(<LowStockProducts />, ROUTE_PERMISSIONS['/low-stock-report'])} />

        <Route path="/products/new" element={protect(<ProductForm />, ['facturacion.add_product'])} />
        <Route path="/products/:id/edit" element={protect(<ProductForm />, ['facturacion.change_product'])} />

        <Route path="/assetsManager" element={protect(<AssetsManager />, ROUTE_PERMISSIONS['/assetsManager'])} />
        <Route path="/assetsForm" element={protect(<AssetForm />, ROUTE_PERMISSIONS['/assetsForm'])} />
        <Route path="/assets/edit/:id" element={protect(<AssetForm />, ['facturacion.change_asset'])} />

        <Route path="/clients" element={protect(<ClientList />, ROUTE_PERMISSIONS['/clients'])} />
        <Route path="/clients/new" element={protect(<ClientForm />, ROUTE_PERMISSIONS['/clients/new'])} />
        <Route path="/clients/:id/edit" element={protect(<ClientForm />, ['facturacion.change_client'])} />

        <Route path="/users" element={protect(<UserList />, ROUTE_PERMISSIONS['/users'])} />
        <Route path="/users/new" element={protect(<UserForm />, ROUTE_PERMISSIONS['/users/new'])} />
        <Route path="/users/:id/edit" element={protect(<UserForm />, ['auth.change_user'])} />

        <Route path="/groups" element={protect(<GroupList />, ROUTE_PERMISSIONS['/groups'])} />
        <Route path="/groups/new" element={protect(<GroupForm />, ROUTE_PERMISSIONS['/groups/new'])} />
        <Route path="/groups/:id/edit" element={protect(<GroupForm />, ['auth.change_group'])} />

        <Route path="/pdf-config" element={protect(<PDFConfig />)} />
      </Routes>
    </Router>
  );
}




export default App;
