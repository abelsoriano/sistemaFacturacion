import React from 'react';
import { Link } from 'react-router-dom';
import { FaTags, FaBoxOpen, FaShoppingCart, FaWarehouse, FaFileInvoice, FaHandshake } from 'react-icons/fa';

function Home() {
  return (
    <div className="container mt-5">
      <h1 className="text-center mb-5">Sistema de Facturación</h1>

      <div className="row g-4 justify-content-center">
        {/* Tarjeta: Categorías */}
        <div className="col-md-3">
          <div className="card text-center h-100 shadow-sm border-primary">
            <div className="card-body">
              <FaTags size={40} className="text-primary mb-3" />
              <h5 className="card-title">Categorías</h5>
              <p className="card-text">
                Administra las categorías de tus productos.
              </p>
              <Link
                to="/dashboard"
                className="btn btn-outline-primary w-100"
              >
                Acceder
              </Link>
            </div>
          </div>
        </div>

        {/* Tarjeta: Productos */}
        <div className="col-md-3">
          <div className="card text-center h-100 shadow-sm border-success">
            <div className="card-body">
              <FaBoxOpen size={40} className="text-success mb-3" />
              <h5 className="card-title">Productos</h5>
              <p className="card-text">Gestiona los productos disponibles.</p>
              <Link
                to="/productsList"
                className="btn btn-outline-success w-100"
              >
                Acceder
              </Link>
            </div>
          </div>
        </div>

        {/* Tarjeta: Ventas */}
        <div className="col-md-3">
          <div className="card text-center h-100 shadow-sm border-warning">
            <div className="card-body">
              <FaShoppingCart size={40} className="text-warning mb-3" />
              <h5 className="card-title">Ventas</h5>
              <p className="card-text">Consulta y administra tus ventas de clientes.</p>
              <Link to="/salesList" className="btn btn-outline-warning w-100">
                Acceder
              </Link>
            </div>
          </div>
        </div>

        {/* Tarjeta: Ventas Rapida */}
        <div className="col-md-3">
          <div className="card text-center h-100 shadow-sm border-warning">
            <div className="card-body">
            <FaShoppingCart size={40} className="text-info mb-3" />
              <h5 className="card-title">Ventas Rapida</h5>
              <p className="card-text">Administra tus ventas Rapida.</p>
              <Link to="/Fastsales" className="btn btn-outline-info w-100">
                Acceder
              </Link>
            </div>
          </div>
        </div>

        {/* Tarjeta: Almacen */}
        <div className="col-md-3">
          <div className="card text-center h-100 shadow-sm border-warning">
            <div className="card-body">
            <FaWarehouse size={40} className="text-cyan-500 mb-3" />
              <h5 className="card-title">Almacen</h5>
              <p className="card-text">Consulta y administrar almacen.</p>
              <Link to="/list-item" className="btn btn-outline-dark w-100">
                Acceder  
              </Link>
            </div>
          </div>
        </div>


         {/* Tarjeta: Mano de Obra */}
         <div className="col-md-3">
          <div className="card text-center h-100 shadow-sm border-warning">
            <div className="card-body">
            <FaHandshake size={40} className= "text-secondary" />
              <h5 className="card-title">Mano de Obra</h5>
              <p className="card-text">Consulta y administrar servicio mano de obra.</p>
              <Link to="/labour-list"  className="btn btn-outline-secondary w-100">
              
                Acceder
              </Link>
            </div>
          </div>
        </div>

        {/* Tarjeta: Factura */}
        <div className="col-md-3">
          <div className="card text-center h-100 shadow-sm border-danger">
            <div className="card-body">
              <FaFileInvoice size={40} className="text-danger mb-3" />
              <h5 className="card-title">Facturación</h5>
              <p className="card-text">Genera nuevas facturas rápidamente.</p>
              <Link
                to="/create-invoice"
                className="btn btn-outline-danger w-100"
              >
                Acceder
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;
