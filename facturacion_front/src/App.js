import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
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


function App() {
  return (
    <Router>
      <Routes>
        
        <Route path="/" element={<Dashboard />} />
        <Route path="/home" element={<Home />} />

        <Route path="/categoriesForm" element={<CategoryForm />} />
        <Route path="/categoriaList" element={<CategoryList />} />
        <Route path="/categoriesForm/:id"  element={<CategoryForm />} /> {/* Para editar */}

        <Route path="/productsList" element={<ProductList />} />
        <Route path="/productsForm" element={<ProductForm />} />
        <Route path="/productsForm/:id" element={<ProductForm />} /> {/* Para editar */}

        <Route path="/sales" element={<SalesForm />} />
        <Route path="/Fastsales" element={<FastSalesForm />} />
        <Route path="/salesList" element={<SalesList />} />
        <Route path="/Fastsales/:id" element={<SalesForm />} />
        
        <Route path="/create-invoice" element={<InvoiceForm />} />
        <Route path="/invoice-list" element={<InvoiceList />} />
         <Route path="/invoices/:id" element={<InvoiceDetail />} />

        <Route path="/register-item" element={<AlmacenForm />} />
        <Route path="/list-item" element={<AlmacenList />} />
        <Route path="/register-item/:id" element={<AlmacenForm />} /> {/* Para editar */}

        <Route path="/register-labour" element={<LabourForm />} />
        <Route path="/labour-list" element={<LabourList />} />
        <Route path="/register-labour/:id" element={<LabourForm />} /> {/* Para editar */}

        <Route path="/sales-reports" element={<SalesPDFReport />} />
        // Agrega esta ruta

        <Route path="/low-stock-report" element={<LowStockProducts />} />

       

      </Routes>
    </Router>
  );
}




export default App;