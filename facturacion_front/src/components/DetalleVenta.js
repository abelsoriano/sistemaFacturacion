// SaleDetailCard.js
// import React from "react";

const DetalleVenta = ({ details, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white rounded-xl shadow-lg w-[600px] max-w-full p-6">
        <h2 className="text-xl font-bold mb-4">Detalles de la venta</h2>
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr>
              <th className="border p-2">Producto</th>
              <th className="border p-2">Cantidad</th>
              <th className="border p-2">Precio</th>
              <th className="border p-2">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {details.map((item, index) => (
              <tr key={index}>
                <td className="border p-2">{item.product_name}</td>
                <td className="border p-2">{item.quantity}</td>
                <td className="border p-2">${parseFloat(item.price).toFixed(2)}</td>
                <td className="border p-2">${parseFloat(item.subtotal).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 flex justify-end space-x-3">
          <button
            className="bg-gray-300 text-gray-800 px-4 py-2 rounded hover:bg-gray-400"
            onClick={onClose}
          >
            Cerrar
          </button>
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            onClick={() => {
              console.log("Redirigir a la factura...");
              // Aquí puedes usar navigate si quieres ir a la factura
              onClose();
            }}
          >
            Ver Factura
          </button>
        </div>
      </div>
    </div>
  );
};

export default DetalleVenta;
