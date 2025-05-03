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



function App() {
  return (
    <Router>
      <Routes>
        
        <Route path="/" element={<Home />} />

        <Route path="/categoriesForm" element={<CategoryForm />} />
        <Route path="/categoriaList" element={<CategoryList />} />
        <Route path="/categoriesForm/:id"  element={<CategoryForm />} /> {/* Para editar */}

        <Route path="/productsList" element={<ProductList />} />
        <Route path="/productsForm" element={<ProductForm />} />
        <Route path="/productsForm/:id" element={<ProductForm />} /> {/* Para editar */}

        <Route path="/sales" element={<SalesForm />} />
        <Route path="/Fastsales" element={<FastSalesForm />} />
        <Route path="/salesList" element={<SalesList />} />

        <Route path="/create-invoice" element={<InvoiceForm />} />
      </Routes>
    </Router>
  );
}




export default App;
