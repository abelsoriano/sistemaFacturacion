import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';

import Home from './components/Home';
import CategoryForm from './components/CategoryForm';
import ProductForm from './components/ProductForm';
import ProductList from './components/ProductList';
import  CategoryList from './components/CategoryList';
import  SalesForm from './components/SalesForm';
import  SalesList from './components/SalesList';
import InvoiceForm from "./components/InvoiceForm";

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


/**
 * Componente para rutas públicas (solo Login)
 * Si ya está autenticado, redirige al home
 */
function PublicRoute({ children }) {
  const token = localStorage.getItem('token');
  
  if (token) {
    return <Navigate to="/" replace />;
  }
  
  return children;
}


function App() {
  return (
    <Router>
      <Routes>

        {/* ============================================ */}
        {/* RUTAS PÚBLICAS - No requieren autenticación */}
        {/* ============================================ */}
        <Route path="/" element={<PublicRoute> <Login /> </PublicRoute>} />
        <Route path="/profile" element={<Profile />} />
        
        <Route path="/dashboard" element={ <ProtectedRoute> <Dashboard /> </ProtectedRoute> }/>
        <Route path="/home" element={ <ProtectedRoute> <Home/> </ProtectedRoute>} />

        <Route path="/categoriesForm" element={<ProtectedRoute> <CategoryForm /> </ProtectedRoute> } />
        <Route path="/categoriaList" element={<ProtectedRoute><CategoryList /></ProtectedRoute>} />
        <Route path="/categoriesForm/:id"  element={<ProtectedRoute><CategoryForm /></ProtectedRoute>} /> {/* Para editar */}

        <Route path="/productsList" element={<ProtectedRoute><ProductList /></ProtectedRoute>} />
        <Route path="/productsForm" element={<ProtectedRoute><ProductForm /></ProtectedRoute>} />
        <Route path="/productsForm/:id" element={<ProtectedRoute><ProductForm /></ProtectedRoute>} /> {/* Para editar */}

        <Route path="/sales" element={<ProtectedRoute><SalesForm /></ProtectedRoute>} />
        <Route path="/Fastsales" element={<ProtectedRoute><FastSalesForm /></ProtectedRoute>} />
        <Route path="/salesList" element={<ProtectedRoute><SalesList /></ProtectedRoute>} />
        <Route path="/Fastsales/:id" element={<ProtectedRoute><SalesForm /></ProtectedRoute>} />
        
        <Route path="/create-invoice" element={<ProtectedRoute><InvoiceForm /></ProtectedRoute>} />
        <Route path="/invoice-list" element={<ProtectedRoute><InvoiceList /></ProtectedRoute>} />
         <Route path="/invoices/:id" element={<ProtectedRoute><InvoiceDetail /></ProtectedRoute>} />

        <Route path="/register-item" element={<ProtectedRoute><AlmacenForm /></ProtectedRoute>} />
        <Route path="/list-item" element={<ProtectedRoute><AlmacenList /></ProtectedRoute>} />
        <Route path="/register-item/:id" element={<ProtectedRoute><AlmacenForm /></ProtectedRoute>} /> {/* Para editar */}

        <Route path="/register-labour" element={<ProtectedRoute><LabourForm /></ProtectedRoute>} />
        <Route path="/labour-list" element={<ProtectedRoute><LabourList /></ProtectedRoute>} />
        <Route path="/register-labour/:id" element={<ProtectedRoute><LabourForm /></ProtectedRoute>} /> {/* Para editar */}

        <Route path="/sales-reports" element={<ProtectedRoute><SalesPDFReport /></ProtectedRoute>} />


        <Route path="/low-stock-report" element={<ProtectedRoute><LowStockProducts /></ProtectedRoute>} />

        <Route path="/products/new" element={<ProtectedRoute><ProductForm /></ProtectedRoute>} />
        <Route path="/products/:id/edit" element={<ProtectedRoute><ProductForm /></ProtectedRoute>} />

        <Route path="/assetsManager" element={<ProtectedRoute><AssetsManager /></ProtectedRoute>} />
        <Route path="/assetsForm" element={<ProtectedRoute><AssetForm /></ProtectedRoute>} />

       

       

      </Routes>
    </Router>
  );
}




export default App;