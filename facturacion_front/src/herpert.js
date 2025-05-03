import Swal from "sweetalert2";

// Función para mostrar una alerta de confirmación
export const showConfirmationAlert = async (title, text) => {
  return await Swal.fire({
    title: title || "¿Estás seguro?",
    text: text || "Esta acción no se puede deshacer.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Sí, eliminar",
    cancelButtonText: "Cancelar",
  });
};

// Función para mostrar una alerta de éxito
export const showSuccessAlert = (title, text) => {
  Swal.fire({
    title: title || "Éxito",
    text: text || "Operación realizada con éxito.",
    icon: "success",
    confirmButtonText: "Aceptar",
  });
};

// Función para mostrar una alerta de error
export const showErrorAlert = (title, text) => {
  Swal.fire({
    title: title || "Error",
    text: text || "Ocurrió un problema.",
    icon: "error",
    confirmButtonText: "Aceptar",
  });
};

// Función Salen
export const showSaleAlert = async (title, text) => {
    return await Swal.fire({
      title: title || "Alert",
      text: text || "El total de la venta no puede ser 0",
      icon: "warning",
      confirmButtonText: "Aceptar",
    });
};
//Generic Alert
export const showGenericAlert = async (title, text) => {
    return await Swal.fire({
      title: text || "Alerta",
      text: text || title,
      icon: "warning",
      confirmButtonText: "Aceptar",
    });
};