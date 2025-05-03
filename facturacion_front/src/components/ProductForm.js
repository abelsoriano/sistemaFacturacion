import React, { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "../services/api"; // Importa la instancia de Axios
import imgPro from "../img/product.jpg";
import "../ProductForm.css";
import { showGenericAlert, showSuccessAlert } from "../herpert";

function ProductForm() {
  const { id } = useParams(); // Obtén el id de la URL
  const navigate = useNavigate(); // Inicializa navigate
  const [error, setError] = useState(null); // Corregido aquí
  const [categories, setCategories] = useState([]); // Lista de categorías
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    price: "",
    stock: "",
    category: "",
  });

  // Obtener las categorías al cargar el componente
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await api.get("categories/");
        setCategories(response.data);
      } catch (err) {
        showGenericAlert("Error al obtener las categorías.");
      }
    };

    fetchCategories();
  }, []);

  // Cargar datos del producto si se está editando
  useEffect(() => {
    if (id) {
      const fetchProduct = async () => {
        try {
          const response = await api.get(`products/${id}/`);
          setFormData(response.data); // Carga los datos en formData
        } catch (err) {
          console.error("Error cargando producto:", err);
        }
      };
      fetchProduct();
    }
  }, [id]);

  // Manejar cambios en los campos del formulario
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // Manejar envío del formulario
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      if (id) {
        // Editar producto existente
        await api.put(`products/${id}/`, formData);
        showSuccessAlert("Producto actualizado correctamente.");
      } else {
        // Crear nuevo producto
        await api.post("products/", formData);
        showSuccessAlert("Producto creado correctamente.");
      }
      navigate("/productsList"); // Redirige a la lista de productos
    } catch (err) {
      console.error("Error guardando producto:", err);
      showGenericAlert("No se pudo guardar el producto. Intenta nuevamente.");
    }
  };

  return (
    <div className="container mt-5">
      <h2 className="text-center mb-4">{id ? "Editar Producto" : "Agregar Producto"}</h2>
      <div className="row">
        <div className="col-md-4">
          <img
            src={imgPro}
            alt="Imagen del producto"
            className="img-fluid"
            style={{ height: "100%" }}
          />
        </div>
        <div className="col-md-8">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label htmlFor="name" className="form-label">
                Nombre del Producto
              </label>
              <input
                type="text"
                className="form-control"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </div>
            <div className="mb-3">
              <label htmlFor="description" className="form-label">
                Descripción
              </label>
              <textarea
                className="form-control"
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
              />
            </div>
            <div className="mb-3">
              <label htmlFor="price" className="form-label">
                Precio
              </label>
              <input
                type="number"
                className="form-control"
                id="price"
                name="price"
                value={formData.price}
                onChange={handleChange}
                required
              />
            </div>
            <div className="mb-3">
              <label htmlFor="stock" className="form-label">
                Stock
              </label>
              <input
                type="number"
                className="form-control"
                id="stock"
                name="stock"
                value={formData.stock}
                onChange={handleChange}
                required
              />
            </div>
            <div className="mb-3">
              <label htmlFor="category" className="form-label">
                Categoría
              </label>
              <select
                className="form-control"
                id="category"
                name="category"
                value={formData.category}
                onChange={handleChange}
                required
              >
                <option value="">Selecciona una categoría</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn btn-primary">
              Guardar
            </button>
            <Link to="/productsList" className="btn btn-danger m-2">
              Cancelar
            </Link>
          </form>
        </div>
      </div>
    </div>
  );
}

export default ProductForm;
