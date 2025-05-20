import React, { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "../services/api";
import imgPro from "../img/product.jpg";
import "../css/ProductForm.css";
import { showGenericAlert, showSuccessAlert } from "../herpert";

function ProductForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    price: "",
    stock: "",
    category: "",
    image: null
  });
  const [previewImage, setPreviewImage] = useState(imgPro);
  const [isLoading, setIsLoading] = useState(false);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({ ...prev, image: file }));
      
      // Crear vista previa
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

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

  useEffect(() => {
    if (id) {
      const fetchProduct = async () => {
        try {
          const response = await api.get(`products/${id}/`);
          const productData = {
            ...response.data,
            category: response.data.category.id // Asegurar que category sea el ID
          };
          setFormData(productData);
          
          // Si hay imagen, establecer la vista previa
          if (response.data.image_url) {
            setPreviewImage(response.data.image_url);
          }
        } catch (err) {
          console.error("Error cargando producto:", err);
          showGenericAlert("Error al cargar el producto.");
        }
      };
      fetchProduct();
    }
  }, [id]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('description', formData.description);
      formDataToSend.append('price', formData.price);
      formDataToSend.append('stock', formData.stock);
      formDataToSend.append('category', formData.category);
      
      // Solo adjuntar la imagen si es un archivo nuevo o si estamos creando
      if (formData.image instanceof File) {
        formDataToSend.append('image', formData.image);
      } else if (!id && !formData.image) {
        // Para nuevos productos sin imagen, puedes omitir el campo o enviar null
        formDataToSend.append('image', '');
      }

      if (id) {
        // Usar PATCH para edición parcial (solo campos modificados)
        await api.patch(`products/${id}/`, formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        showSuccessAlert("Producto actualizado correctamente.");
      } else {
        await api.post("products/", formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        showSuccessAlert("Producto creado correctamente.");
      }
      navigate("/productsList");
    } catch (err) {
      console.error("Error guardando producto:", err);
      showGenericAlert("No se pudo guardar el producto. Intenta nuevamente.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mt-5">
      <h2 className="text-center mb-4">{id ? "Editar Producto" : "Agregar Producto"}</h2>
      <div className="row">
        <div className="col-md-4">
          <div className="image-upload-container">
            <img
              src={previewImage}
              alt="Preview del producto"
              className="img-fluid product-image"
            />
            <div className="mt-3">
              <input
                type="file"
                id="image-upload"
                accept="image/*"
                onChange={handleImageChange}
                className="d-none"
              />
              <label htmlFor="image-upload" className="btn btn-outline-secondary">
                {formData.image ? "Cambiar imagen" : "Seleccionar imagen"}
              </label>
              {formData.image && (
                <button 
                  type="button" 
                  className="btn btn-outline-danger ms-2"
                  onClick={() => {
                    setFormData({...formData, image: null});
                    setPreviewImage(imgPro);
                  }}
                >
                  Eliminar
                </button>
              )}
            </div>
            <small className="text-muted">(Opcional)</small>
          </div>
        </div>
        <div className="col-md-8">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label htmlFor="name" className="form-label">
                Nombre del Producto *
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
                rows="3"
              />
            </div>
            <div className="row">
              <div className="col-md-6 mb-3">
                <label htmlFor="price" className="form-label">
                  Precio *
                </label>
                <div className="input-group">
                  <span className="input-group-text">$</span>
                  <input
                    type="number"
                    className="form-control"
                    id="price"
                    name="price"
                    value={formData.price}
                    onChange={handleChange}
                    min="0"
                    step="0.01"
                    required
                  />
                </div>
              </div>
              <div className="col-md-6 mb-3">
                <label htmlFor="stock" className="form-label">
                  Stock *
                </label>
                <input
                  type="number"
                  className="form-control"
                  id="stock"
                  name="stock"
                  value={formData.stock}
                  onChange={handleChange}
                  min="0"
                  required
                />
              </div>
            </div>
            <div className="mb-3">
              <label htmlFor="category" className="form-label">
                Categoría *
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
            <div className="d-flex justify-content-end mt-4">
              <Link to="/productsList" className="btn btn-outline-secondary me-2">
                Cancelar
              </Link>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Guardando...
                  </>
                ) : (
                  "Guardar"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default ProductForm;