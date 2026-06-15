import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "../services/api";
import imgPro from "../img/product.jpg";
import "../css/ProductForm.css";
import { showGenericAlert } from "../herpert";
import { notify } from "../utils/notify";

function ProductForm() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Estados existentes
  const [categories, setCategories] = useState([]);
  const [filteredCategories, setFilteredCategories] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [categoryForm, setCategoryForm] = useState({ name: "", description: "" });
  const [categorySaving, setCategorySaving] = useState(false);
  const [categoryError, setCategoryError] = useState("");
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
  const [errors, setErrors] = useState({});

  // Estados para impresión - ASEGÚRATE DE TENER ESTOS
  const [showPrintModal, setShowPrintModal] = useState(false);
  const [printQuantity, setPrintQuantity] = useState(1);
  const [barcodeImage, setBarcodeImage] = useState(null);
  const [availablePrinters, setAvailablePrinters] = useState([]);  // ← IMPORTANTE
  const [selectedPrinter, setSelectedPrinter] = useState('USB001'); // ← IMPORTANTE
  const [loadingPrinters, setLoadingPrinters] = useState(false);    // ← IMPORTANTE

  const dropdownRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);
  const [submitMode, setSubmitMode] = useState('save');

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = "El nombre del producto es requerido.";
    }

    if (!formData.price || formData.price <= 0) {
      newErrors.price = "El precio debe ser mayor a 0.";
    }

    if (!formData.stock || formData.stock < 0) {
      newErrors.stock = "El stock no puede ser negativo.";
    }

    if (!formData.category) {
      newErrors.category = categories.length === 0
        ? "Debes crear una categoría antes de guardar el producto."
        : "Selecciona una categoría para este producto.";
    }

    setErrors(newErrors);
    if (newErrors.category) {
      notify.warning("Categoría requerida", newErrors.category);
    }
    return Object.keys(newErrors).length === 0;
  };

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

  const fetchCategories = async () => {
    try {
      const response = await api.get("categories/");
      setCategories(response.data);
      setFilteredCategories(response.data.slice(0, 10));
      return response.data;
    } catch (err) {
      notify.error("Error al obtener las categorías.");
      return [];
    }
  };

  // Cargar categorías
  useEffect(() => {
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

  const openCategoryModal = () => {
    setCategoryForm({ name: searchTerm || "", description: "" });
    setCategoryError("");
    setShowCategoryModal(true);
  };

  const handleCategoryFormChange = (e) => {
    setCategoryForm({
      ...categoryForm,
      [e.target.name]: e.target.value,
    });
    setCategoryError("");
  };

  const handleCreateCategory = async (e) => {
    e.preventDefault();
    const name = categoryForm.name.trim();

    if (!name) {
      setCategoryError("El nombre de la categoría es obligatorio.");
      return;
    }

    setCategorySaving(true);
    try {
      const response = await api.post("categories/", {
        name,
        description: categoryForm.description,
      });
      const createdCategory = response.data;
      await fetchCategories();
      handleCategorySelect(createdCategory);
      setShowCategoryModal(false);
      notify.success("Categoría creada", "La nueva categoría quedó seleccionada.");
    } catch (err) {
      console.error("Error creando categoría:", err);
      const detail = err.response?.data?.detail;
      const nameError = Array.isArray(err.response?.data?.name)
        ? err.response.data.name[0]
        : null;
      setCategoryError(detail || nameError || "No se pudo crear la categoría.");
    } finally {
      setCategorySaving(false);
    }
  };

  const handleSearchFocus = () => {
    setShowDropdown(true);
    if (!searchTerm) {
      setFilteredCategories(categories.slice(0, 10));
    }
  };

  const handleSubmit = async (e, mode = 'save') => {
    if (e) {
      e.preventDefault();
    }

    if (!validateForm()) {
      return;
    }

    setSubmitMode(mode);
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

      if (id) {
        await api.patch(`products/${id}/`, formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        notify.success("Producto actualizado correctamente.");
      } else {
        await api.post("products/", formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        notify.success("Producto creado correctamente.");

      }

      if (mode === 'save_and_new') {
        notify.success("Producto guardado", "Puedes crear un nuevo producto ahora.");
        setFormData({
          name: "",
          description: "",
          price: "",
          stock: "",
          category: "",
          categoryName: "",
          image: null,
          barcode: ""
        });
        setPreviewImage(imgPro);
        setErrors({});
        setSearchTerm("");
        setBarcodeImage(null);
        setShowDropdown(false);
        if (id) {
          navigate('/productsForm', { replace: true });
        }
        return;
      }

      navigate('/productsList');

    } catch (err) {
      console.error("Error guardando producto:", err);
      notify.error("No se pudo guardar el producto", "Intenta nuevamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadPrinters = async () => {
    setLoadingPrinters(true);
    try {
      const response = await api.get('products/list-printers/');
      // console.log("Impresoras detectadas:", response.data);

      if (response.data.printers && response.data.printers.length > 0) {
        setAvailablePrinters(response.data.printers);
        // Seleccionar automáticamente la primera impresora detectada
        setSelectedPrinter(response.data.printers[0].port || 'USB001');
        notify.success(`${response.data.printers.length} impresora(s) detectada(s)`);
      } else {
        setAvailablePrinters([{ name: 'USB001 (Por defecto)', port: 'USB001' }]);
        notify.warning('No se detectaron impresoras', 'Usando USB001 por defecto.');
      }
    } catch (err) {
      console.error("Error cargando impresoras:", err);
      setAvailablePrinters([{ name: 'USB001 (Por defecto)', port: 'USB001' }]);
      notify.warning('Error al detectar impresoras', 'Usando USB001 por defecto.');
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
      const response = await api.post('products/print-direct/', {
        product_id: parseInt(productId),
        quantity: parseInt(printQuantity),
        printer_name: selectedPrinter
      });

      if (response.data.success) {
        notify.success(response.data.message || "Etiqueta enviada a la impresora correctamente.");
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
      // console.log("Enviando datos:", { product_id: parseInt(productId), quantity: printQuantity });

      const response = await api.post('products/print-label/', {
        product_id: parseInt(productId),  // Asegurar que sea número
        quantity: parseInt(printQuantity)  // Asegurar que sea número
      });

      // console.log("Respuesta recibida:", response.data);

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

      notify.success(`${printQuantity} etiqueta(s) generada(s)`, "Envía el archivo a tu impresora Zebra.");
      setShowPrintModal(false);
    } catch (err) {
      console.error("Error completo:", err);
      console.error("Respuesta del servidor:", err.response?.data);

      const errorMsg = err.response?.data?.error || "Error al generar la etiqueta.";
      showGenericAlert(errorMsg);
    }
  };

  return (
    <div className="product-form-page">
      <header className="pf-header">
        <div>
          <span className="pf-eyebrow">Inventario</span>
          <h1>{id ? "Editar producto" : "Agregar producto"}</h1>
          <p>Gestiona datos básicos, precio, stock, categoría, imagen y etiqueta del producto.</p>
        </div>
      </header>

      <form className="pf-layout" onSubmit={handleSubmit}>
        <aside className="pf-side">
          <section className="pf-card">
            <div className="pf-card-head">
              <div>
                <span>Imagen</span>
                <h2>Vista del producto</h2>
              </div>
            </div>
            <div className="pf-image-panel">
              <img src={previewImage} alt="Preview del producto" className="pf-product-image" />
              <input type="file" id="image-upload" accept="image/*" onChange={handleImageChange} className="pf-hidden-input" />
              <div className="pf-image-actions">
                <label htmlFor="image-upload" className="pf-btn secondary">
                  {formData.image ? "Cambiar imagen" : "Seleccionar imagen"}
                </label>
                {formData.image && (
                  <button
                    type="button"
                    className="pf-btn danger"
                    onClick={() => {
                      setFormData({ ...formData, image: null });
                      setPreviewImage(imgPro);
                    }}
                  >
                    Eliminar
                  </button>
                )}
              </div>
              <small>Opcional. No cambia la lógica actual de carga.</small>
            </div>
          </section>

          <section className="pf-card">
            <div className="pf-card-head">
              <div>
                <span>Barcode / etiqueta</span>
                <h2>Código interno</h2>
              </div>
            </div>
            <div className="pf-barcode-panel">
              {barcodeImage ? (
                <>
                  <img src={barcodeImage} alt="Código de barras" className="pf-barcode-image" />
                  <strong>{formData.barcode}</strong>
                  <button type="button" className="pf-btn success full" onClick={() => setShowPrintModal(true)}>
                    Imprimir etiqueta
                  </button>
                </>
              ) : (
                <div className="pf-empty-box">
                  <strong>Sin etiqueta disponible</strong>
                  <p>Guarda el producto para generar y visualizar el código de barras.</p>
                </div>
              )}
            </div>
          </section>
        </aside>

        <main className="pf-main">
          <section className="pf-card">
            <div className="pf-card-head">
              <div>
                <span>Datos básicos</span>
                <h2>Identificación del producto</h2>
              </div>
            </div>
            <div className="pf-card-body">
              <label className="pf-field">
                <span>Nombre del producto *</span>
                <input
                  type="text"
                  className={errors.name ? 'is-invalid' : ''}
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                />
                {errors.name && <small className="pf-error">{errors.name}</small>}
              </label>

              <label className="pf-field">
                <span>Descripción</span>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  rows="4"
                />
              </label>
            </div>
          </section>

          <section className="pf-grid-two">
            <div className="pf-card">
              <div className="pf-card-head">
                <div>
                  <span>Precio / costo / impuestos</span>
                  <h2>Precio de venta</h2>
                </div>
              </div>
              <div className="pf-card-body">
                <label className="pf-field">
                  <span>Precio de venta *</span>
                  <div className="pf-money-input">
                    <b>$</b>
                    <input
                      type="number"
                      className={errors.price ? 'is-invalid' : ''}
                      id="price"
                      name="price"
                      value={formData.price}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                      required
                    />
                  </div>
                  {errors.price && <small className="pf-error">{errors.price}</small>}
                </label>
                <div className="pf-note-box">
                  Este producto usa solo precio de venta por ahora. Costo e impuestos
                  avanzados requieren una fase funcional posterior.
                </div>
              </div>
            </div>

            <div className="pf-card">
              <div className="pf-card-head">
                <div>
                  <span>Inventario / stock</span>
                  <h2>Existencia inicial</h2>
                </div>
              </div>
              <div className="pf-card-body">
                <label className="pf-field">
                  <span>Stock *</span>
                  <input
                    type="number"
                    className={errors.stock ? 'is-invalid' : ''}
                    id="stock"
                    name="stock"
                    value={formData.stock}
                    onChange={handleChange}
                    min="0"
                    required
                  />
                  {errors.stock && <small className="pf-error">{errors.stock}</small>}
                </label>
              </div>
            </div>
          </section>

          <section className="pf-card">
            <div className="pf-card-head">
              <div>
                <span>Categoría / almacén</span>
                <h2>Clasificación</h2>
              </div>
            </div>
            <div className="pf-card-body">
              <label className="pf-field" ref={dropdownRef}>
                <span>Categoría *</span>
                {categories.length === 0 ? (
                  <div className="pf-category-empty-state">
                    <div>
                      <strong>Debes crear una categoría antes de guardar el producto.</strong>
                      <span>La categoría organiza inventario, reportes y búsqueda de productos.</span>
                    </div>
                    <button
                      type="button"
                      className="pf-btn secondary pf-compact-btn"
                      onClick={openCategoryModal}
                    >
                      Nueva categoría
                    </button>
                  </div>
                ) : (
                  <div className="pf-category-row">
                    <div className="pf-category-wrap">
                      <input
                        type="text"
                        className={errors.category ? 'is-invalid' : ''}
                        id="category-search"
                        placeholder="Buscar o seleccionar categoría..."
                        value={searchTerm}
                        onChange={handleSearchChange}
                        onFocus={handleSearchFocus}
                        required
                      />
                      {showDropdown && filteredCategories.length > 0 && (
                        <div className="category-dropdown">
                          {filteredCategories.map((category) => (
                            <button
                              type="button"
                              key={category.id}
                              className="category-dropdown-item"
                              onClick={() => handleCategorySelect(category)}
                            >
                              {category.name}
                            </button>
                          ))}
                        </div>
                      )}
                      {showDropdown && filteredCategories.length === 0 && searchTerm && (
                        <div className="category-dropdown">
                          <div className="category-dropdown-empty">No se encontraron categorías</div>
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      className="pf-btn secondary pf-compact-btn"
                      onClick={openCategoryModal}
                    >
                      Nueva categoría
                    </button>
                  </div>
                )}
                {errors.category && <small className="pf-error">{errors.category}</small>}
              </label>

              <input type="hidden" name="category" value={formData.category} required />
              <div className="pf-note-box">
                El producto actual no tiene campo de almacén asignado. El módulo de
                almacén se gestiona por separado.
              </div>
            </div>
          </section>

          <section className="pf-card">
            <div className="pf-card-body pf-submit-row">
              <Link to="/productsList" className="pf-btn secondary">Cancelar</Link>
              <button
                type="button"
                className="pf-btn secondary"
                onClick={(e) => handleSubmit(e, 'save_and_new')}
                disabled={isLoading}
                title="Guardar este producto y preparar un nuevo formulario"
              >
                {isLoading && submitMode === 'save_and_new' ? 'Guardando...' : 'Guardar y crear otro'}
              </button>
              <button type="submit" className="pf-btn primary" disabled={isLoading}>
                {isLoading && submitMode === 'save' ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </section>
        </main>
      </form>

      {showPrintModal && (
        <div className="pf-modal-backdrop">
          <div className="pf-modal">
            <div className="pf-modal-head">
              <div>
                <span>Etiqueta</span>
                <h2>Imprimir etiquetas</h2>
              </div>
              <button type="button" className="pf-icon-btn" onClick={() => setShowPrintModal(false)}>×</button>
            </div>
            <div className="pf-modal-body">
              <label className="pf-field">
                <span>Cantidad de etiquetas</span>
                <input
                  type="number"
                  value={printQuantity}
                  onChange={(e) => setPrintQuantity(parseInt(e.target.value) || 1)}
                  min="1"
                  max="100"
                />
              </label>

              <label className="pf-field">
                <span>Impresora</span>
                <div className="pf-printer-row">
                  <select value={selectedPrinter} onChange={(e) => setSelectedPrinter(e.target.value)} disabled={loadingPrinters}>
                    {availablePrinters.length > 0 ? (
                      availablePrinters.map((printer, idx) => (
                        <option key={idx} value={printer.port}>{printer.name} ({printer.port})</option>
                      ))
                    ) : (
                      <option value="USB001">USB001 (Por defecto)</option>
                    )}
                  </select>
                  <button className="pf-btn secondary" onClick={loadPrinters} disabled={loadingPrinters} type="button" title="Detectar impresoras">
                    {loadingPrinters ? "Detectando..." : "Detectar"}
                  </button>
                </div>
                <small>Detecta impresoras disponibles o usa USB001 por defecto.</small>
              </label>

              <div className="pf-info-box">
                <strong>Impresión directa:</strong> envía a la impresora Zebra conectada por USB.
                <br />
                <strong>Descargar ZPL:</strong> genera el archivo para imprimir manualmente.
              </div>
            </div>
            <div className="pf-modal-actions">
              <button type="button" className="pf-btn secondary" onClick={() => setShowPrintModal(false)}>Cancelar</button>
              <button type="button" className="pf-btn secondary" onClick={handlePrintLabel} title="Descargar archivo ZPL">Descargar ZPL</button>
              <button type="button" className="pf-btn success" onClick={handlePrintDirect} title="Enviar directamente a la impresora">Imprimir directo</button>
            </div>
          </div>
        </div>
      )}

      {showCategoryModal && (
        <div className="pf-modal-backdrop">
          <div className="pf-modal pf-category-modal">
            <div className="pf-modal-head">
              <div>
                <span>Inventario</span>
                <h2>Nueva categoría</h2>
              </div>
              <button type="button" className="pf-icon-btn" onClick={() => setShowCategoryModal(false)}>×</button>
            </div>
            <form onSubmit={handleCreateCategory}>
              <div className="pf-modal-body">
                {categoryError && (
                  <div className="pf-form-alert" role="alert">
                    {categoryError}
                  </div>
                )}
                <label className="pf-field">
                  <span>Nombre *</span>
                  <input
                    name="name"
                    value={categoryForm.name}
                    onChange={handleCategoryFormChange}
                    placeholder="Ej. Bebidas, Repuestos, Servicios"
                    required
                  />
                </label>
                <label className="pf-field">
                  <span>Descripción</span>
                  <textarea
                    name="description"
                    value={categoryForm.description}
                    onChange={handleCategoryFormChange}
                    rows="3"
                    placeholder="Descripción opcional"
                  />
                </label>
              </div>
              <div className="pf-modal-actions">
                <button type="button" className="pf-btn secondary" onClick={() => setShowCategoryModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="pf-btn primary" disabled={categorySaving}>
                  {categorySaving ? "Creando..." : "Crear y seleccionar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProductForm;
