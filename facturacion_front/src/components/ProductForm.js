import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "../services/api";
import imgPro from "../img/product.jpg";
import "../css/ProductForm.css";
import { showGenericAlert, showSuccessAlert } from "../herpert";

function ProductForm() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Estados existentes
  const [categories, setCategories] = useState([]);
  const [filteredCategories, setFilteredCategories] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    price: "",
    stock: "",
    category: "",
    categoryName: "",
    image: null,
    barcode: ""
  });
  const [previewImage, setPreviewImage] = useState(imgPro);
  const [isLoading, setIsLoading] = useState(false);

  // Estados para impresión - ASEGÚRATE DE TENER ESTOS
  const [showPrintModal, setShowPrintModal] = useState(false);
  const [printQuantity, setPrintQuantity] = useState(1);
  const [barcodeImage, setBarcodeImage] = useState(null);
  const [availablePrinters, setAvailablePrinters] = useState([]);  // ← IMPORTANTE
  const [selectedPrinter, setSelectedPrinter] = useState('USB001'); // ← IMPORTANTE
  const [loadingPrinters, setLoadingPrinters] = useState(false);    // ← IMPORTANTE

  const dropdownRef = useRef(null);

  // Cerrar dropdown al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({ ...prev, image: file }));

      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Cargar categorías
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await api.get("categories/");
        setCategories(response.data);
        setFilteredCategories(response.data.slice(0, 10));
      } catch (err) {
        showGenericAlert("Error al obtener las categorías.");
      }
    };

    fetchCategories();
  }, []);

  // Cargar producto para edición
  useEffect(() => {
    if (id) {
      const fetchProduct = async () => {
        try {
          const response = await api.get(`products/${id}/`);

          const productData = {
            ...response.data,
            category: response.data.category || "",
            categoryName: response.data.category_name || ""
          };

          setFormData(productData);

          if (response.data.category_name) {
            setSearchTerm(response.data.category_name);
          }

          if (response.data.image_url) {
            setPreviewImage(response.data.image_url);
          }

          // Cargar imagen del código de barras si existe
          if (response.data.barcode) {
            loadBarcodeImage(id);
          }
        } catch (err) {
          console.error("Error cargando producto:", err);
          showGenericAlert("Error al cargar el producto.");
        }
      };
      fetchProduct();
    }
  }, [id]);

  // Cargar imagen del código de barras
  const loadBarcodeImage = async (productId) => {
    try {
      const response = await api.get(`products/${productId}/barcode-image/`);
      setBarcodeImage(response.data.image);
    } catch (err) {
      console.error("Error cargando código de barras:", err);
    }
  };

  // Filtrar categorías basado en la búsqueda
  useEffect(() => {
    if (searchTerm) {
      const filtered = categories.filter(category =>
        category.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredCategories(filtered.slice(0, 10));
    } else {
      setFilteredCategories(categories.slice(0, 10));
    }
  }, [searchTerm, categories]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setShowDropdown(true);
  };

  const handleCategorySelect = (category) => {
    setFormData({
      ...formData,
      category: category.id,
      categoryName: category.name
    });
    setSearchTerm(category.name);
    setShowDropdown(false);
  };

  const handleSearchFocus = () => {
    setShowDropdown(true);
    if (!searchTerm) {
      setFilteredCategories(categories.slice(0, 10));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.category) {
      showGenericAlert("Por favor selecciona una categoría.");
      return;
    }

    setIsLoading(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('description', formData.description);
      formDataToSend.append('price', formData.price);
      formDataToSend.append('stock', formData.stock);
      formDataToSend.append('category', formData.category);

      if (formData.image instanceof File) {
        formDataToSend.append('image', formData.image);
      } else if (!id && !formData.image) {
        formDataToSend.append('image', '');
      }

      let savedProduct;
      if (id) {
        const response = await api.patch(`products/${id}/`, formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        savedProduct = response.data;
        showSuccessAlert("Producto actualizado correctamente.");
      } else {
        const response = await api.post("products/", formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        savedProduct = response.data;
        showSuccessAlert("Producto creado correctamente.");

        // IMPORTANTE: Actualizar formData con el ID del nuevo producto
        setFormData(prev => ({
          ...prev,
          id: savedProduct.id,  // ← Guardar el ID
          barcode: savedProduct.barcode
        }));

        // Cargar imagen del código de barras
        if (savedProduct.id && savedProduct.barcode) {
          await loadBarcodeImage(savedProduct.id);
        }

        // Navegar a la URL de edición para que el ID esté en la URL
        navigate(`/products/${savedProduct.id}/edit`, { replace: true });
      }

    } catch (err) {
      console.error("Error guardando producto:", err);
      showGenericAlert("No se pudo guardar el producto. Intenta nuevamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadPrinters = async () => {
    setLoadingPrinters(true);
    try {
      const response = await api.get('products/list-printers/');
      console.log("Impresoras detectadas:", response.data);

      if (response.data.printers && response.data.printers.length > 0) {
        setAvailablePrinters(response.data.printers);
        // Seleccionar automáticamente la primera impresora detectada
        setSelectedPrinter(response.data.printers[0].port || 'USB001');
        showSuccessAlert(`${response.data.printers.length} impresora(s) detectada(s)`);
      } else {
        setAvailablePrinters([{ name: 'USB001 (Por defecto)', port: 'USB001' }]);
        showGenericAlert('No se detectaron impresoras. Usando USB001 por defecto.');
      }
    } catch (err) {
      console.error("Error cargando impresoras:", err);
      setAvailablePrinters([{ name: 'USB001 (Por defecto)', port: 'USB001' }]);
      showGenericAlert('Error al detectar impresoras. Usando USB001 por defecto.');
    } finally {
      setLoadingPrinters(false);
    }
  };

  // Función para imprimir directamente
  const handlePrintDirect = async () => {
    const productId = id || formData.id;

    if (!productId) {
      showGenericAlert("Primero debes guardar el producto para imprimir la etiqueta.");
      return;
    }

    if (!formData.barcode) {
      showGenericAlert("Este producto no tiene código de barras generado.");
      return;
    }

    try {
      console.log("Imprimiendo directamente...", {
        product_id: parseInt(productId),
        quantity: printQuantity,
        printer_name: selectedPrinter
      });

      const response = await api.post('products/print-direct/', {
        product_id: parseInt(productId),
        quantity: parseInt(printQuantity),
        printer_name: selectedPrinter
      });

      console.log("Respuesta:", response.data);

      if (response.data.success) {
        showSuccessAlert(response.data.message || "Etiqueta enviada a la impresora correctamente.");
        setShowPrintModal(false);
      } else {
        showGenericAlert(response.data.error || "Error al imprimir directamente.");
      }
    } catch (err) {
      console.error("Error imprimiendo:", err);
      console.error("Respuesta del servidor:", err.response?.data);

      const errorMsg = err.response?.data?.error || "Error al enviar a la impresora.";
      const suggestion = err.response?.data?.suggestion;

      if (suggestion) {
        showGenericAlert(`${errorMsg}\n\n${suggestion}`);
      } else {
        showGenericAlert(errorMsg);
      }
    }
  };

  // Función para imprimir etiqueta
  const handlePrintLabel = async () => {
    // Obtener el ID desde la URL o desde formData
    const productId = id || formData.id;

    if (!productId) {
      showGenericAlert("Primero debes guardar el producto para imprimir la etiqueta.");
      return;
    }

    if (!formData.barcode) {
      showGenericAlert("Este producto no tiene código de barras generado.");
      return;
    }

    try {
      console.log("Enviando datos:", { product_id: parseInt(productId), quantity: printQuantity });

      const response = await api.post('products/print-label/', {
        product_id: parseInt(productId),  // Asegurar que sea número
        quantity: parseInt(printQuantity)  // Asegurar que sea número
      });

      console.log("Respuesta recibida:", response.data);

      if (response.data.success === false || response.data.error) {
        showGenericAlert(response.data.error || "Error al generar la etiqueta.");
        return;
      }

      // Crear un blob con el contenido ZPL y descargarlo
      const zplContent = response.data.zpl;
      const blob = new Blob([zplContent], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `etiqueta_${formData.name.replace(/\s+/g, '_')}.zpl`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      showSuccessAlert(`${printQuantity} etiqueta(s) generada(s). Envía el archivo a tu impresora Zebra.`);
      setShowPrintModal(false);
    } catch (err) {
      console.error("Error completo:", err);
      console.error("Respuesta del servidor:", err.response?.data);

      const errorMsg = err.response?.data?.error || "Error al generar la etiqueta.";
      showGenericAlert(errorMsg);
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
                    setFormData({ ...formData, image: null });
                    setPreviewImage(imgPro);
                  }}
                >
                  Eliminar
                </button>
              )}
            </div>
            <small className="text-muted">(Opcional)</small>

            {/* Mostrar código de barras si existe */}
            {barcodeImage && (
              <div className="mt-4 border rounded p-3">
                <h6 className="text-center mb-2">Código de Barras</h6>
                <img
                  src={barcodeImage}
                  alt="Código de barras"
                  className="img-fluid"
                  style={{ maxWidth: '100%' }}
                />
                <p className="text-center mt-2 mb-2">
                  <small><strong>{formData.barcode}</strong></small>
                </p>
                <button
                  type="button"
                  className="btn btn-success btn-sm w-100"
                  onClick={() => setShowPrintModal(true)}
                >
                  🖨️ Imprimir Etiqueta
                </button>
              </div>
            )}
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

            {/* Campo de categoría con búsqueda */}
            <div className="mb-3">
              <label htmlFor="category-search" className="form-label">
                Categoría *
              </label>
              <div className="position-relative" ref={dropdownRef}>
                <input
                  type="text"
                  className="form-control"
                  id="category-search"
                  placeholder="Buscar categoría..."
                  value={searchTerm}
                  onChange={handleSearchChange}
                  onFocus={handleSearchFocus}
                  required
                />

                {showDropdown && filteredCategories.length > 0 && (
                  <div
                    className="position-absolute w-100 bg-white border mt-1 rounded shadow-sm z-3 category-dropdown"
                    style={{ maxHeight: '200px', overflowY: 'auto' }}
                  >
                    {filteredCategories.map((category) => (
                      <div
                        key={category.id}
                        className="dropdown-item cursor-pointer"
                        onClick={() => handleCategorySelect(category)}
                        style={{
                          cursor: 'pointer',
                          padding: '8px 12px',
                          borderBottom: '1px solid #f8f9fa'
                        }}
                      >
                        {category.name}
                      </div>
                    ))}
                  </div>
                )}

                {showDropdown && filteredCategories.length === 0 && searchTerm && (
                  <div className="position-absolute w-100 bg-white border mt-1 rounded shadow-sm z-3">
                    <div className="dropdown-item text-muted">
                      No se encontraron categorías
                    </div>
                  </div>
                )}
              </div>

              <input
                type="hidden"
                name="category"
                value={formData.category}
                required
              />
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


      {/* Modal para imprimir etiquetas */}
      {showPrintModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Imprimir Etiquetas</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowPrintModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                {/* Cantidad de etiquetas */}
                <div className="mb-3">
                  <label className="form-label">Cantidad de etiquetas:</label>
                  <input
                    type="number"
                    className="form-control"
                    value={printQuantity}
                    onChange={(e) => setPrintQuantity(parseInt(e.target.value) || 1)}
                    min="1"
                    max="100"
                  />
                </div>

                {/* Selector de impresora */}
                <div className="mb-3">
                  <label className="form-label">Impresora:</label>
                  <div className="input-group">
                    <select
                      className="form-select"
                      value={selectedPrinter}
                      onChange={(e) => setSelectedPrinter(e.target.value)}
                      disabled={loadingPrinters}
                    >
                      {availablePrinters.length > 0 ? (
                        availablePrinters.map((printer, idx) => (
                          <option key={idx} value={printer.port}>
                            {printer.name} ({printer.port})
                          </option>
                        ))
                      ) : (
                        <option value="USB001">USB001 (Por defecto)</option>
                      )}
                    </select>
                    <button
                      className="btn btn-outline-secondary"
                      onClick={loadPrinters}
                      disabled={loadingPrinters}
                      type="button"
                      title="Detectar impresoras"
                    >
                      {loadingPrinters ? "⏳" : "🔄"}
                    </button>
                  </div>
                  <small className="text-muted">
                    Haz clic en 🔄 para detectar impresoras automáticamente
                  </small>
                </div>

                {/* Información */}
                <div className="alert alert-info mb-0">
                  <small>
                    <strong>🖨️ Impresión Directa:</strong> Envía directamente a la impresora Zebra conectada por USB.<br />
                    <strong>📥 Descargar ZPL:</strong> Descarga el archivo para imprimir manualmente.
                  </small>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowPrintModal(false)}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn btn-outline-primary"
                  onClick={handlePrintLabel}
                  title="Descargar archivo ZPL"
                >
                  📥 Descargar ZPL
                </button>
                <button
                  type="button"
                  className="btn btn-success"
                  onClick={handlePrintDirect}
                  title="Enviar directamente a la impresora"
                >
                  🖨️ Imprimir Directo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}   </div>
  );
}

export default ProductForm;