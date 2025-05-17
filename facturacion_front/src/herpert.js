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
      cancelButtonText: "Cancelar"
    });
};

export const showGenerAlertSioNo = async (title, text) => {
  const result = await Swal.fire({
    title: title || "¿Estás seguro?",
    text: text || "",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Sí",
    cancelButtonText: "No"
  });

  return result.isConfirmed;
};

// Estilos CSS para el formulario
export const styles = {
  formContainer: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08)',
    padding: '24px',
    maxWidth: '1000px',
    margin: '0 auto',
    fontFamily: 'Arial, sans-serif',
  },
  formHeader: {
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '24px',
    color: '#333',
    borderBottom: '1px solid #eaeaea',
    paddingBottom: '16px',
    display: 'flex',
    alignItems: 'center',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '20px',
    marginBottom: '24px',
  },
  formGroup: {
    marginBottom: '16px',
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#444',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    transition: 'border-color 0.3s, box-shadow 0.3s',
    boxSizing: 'border-box',
    outline: 'none',
  },
  inputFocus: {
    borderColor: '#3b82f6',
    boxShadow: '0 0 0 2px rgba(59, 130, 246, 0.2)',
  },
  inputWithIcon: {
    paddingLeft: '36px',
    position: 'relative',
  },
  iconWrapper: {
    position: 'absolute',
    left: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#9ca3af',
  },
  select: {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: '#fff',
    transition: 'border-color 0.3s, box-shadow 0.3s',
    appearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23666666'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 12px center',
    backgroundSize: '16px',
    outline: 'none',
  },
  textarea: {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    transition: 'border-color 0.3s, box-shadow 0.3s',
    resize: 'none',
    minHeight: '120px',
    outline: 'none',
  },
  buttonContainer: {
    display: 'flex',
    justifyContent: 'flex-end',
    paddingTop: '16px',
    borderTop: '1px solid #eaeaea',
  },

  containerAlmacen: {
    display: 'flex',
    justifyContent: 'flex-end',
    paddingTop: '12px',
    backgroundImage: 'linear-gradient(to right, transparent 70%, #eaeaea 70%)',
    backgroundPosition: 'top',
    backgroundSize: '100% 1px', // Ancho 100%, altura 1px
    backgroundRepeat: 'no-repeat',
  },
  
  button: {
    padding: '10px 16px',
    fontSize: '14px',
    fontWeight: '500',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
  },
  cancelButton: {
    backgroundColor: '#fff',
    color: '#444',
    marginRight: '12px',
    border: '1px solid #ddd',
  },
  cancelButtonHover: {
    backgroundColor: '#f3f4f6',
  },
  submitButton: {
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
  },
  submitButtonHover: {
    backgroundColor: '#2563eb',
  },
  submitButtonDisabled: {
    opacity: '0.7',
    cursor: 'not-allowed',
  },
  alertBox: {
    padding: '16px',
    borderRadius: '4px',
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
  },
  successAlert: {
    backgroundColor: '#ecfdf5',
    color: '#047857',
  },
  errorAlert: {
    backgroundColor: '#fef2f2',
    color: '#b91c1c',
  },
  icon: {
    marginRight: '8px',
    width: '20px',
    height: '20px',
  }
};


// Estilos CSS para la lista de almacén
export const stylesAlmacens = {
  container: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08)',
    padding: '24px',
    maxWidth: '1200px',
    margin: '0 auto',
    fontFamily: 'Arial, sans-serif',
  },
  header: {
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '24px',
    color: '#333',
    borderBottom: '1px solid #eaeaea',
    paddingBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
  },
  searchFilterContainer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
    flexWrap: 'wrap',
    gap: '16px',
  },
  searchContainer: {
    position: 'relative',
    flex: '1',
    minWidth: '250px',
    maxWidth: '400px',
  },
  searchInput: {
    width: '100%',
    padding: '10px 12px 10px 40px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    transition: 'border-color 0.3s, box-shadow 0.3s',
    boxSizing: 'border-box',
    outline: 'none',
  },
  searchIcon: {
    position: 'absolute',
    left: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#9ca3af',
  },
  filtersContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  select: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: '#fff',
    transition: 'border-color 0.3s, box-shadow 0.3s',
    appearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23666666'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 12px center',
    backgroundSize: '16px',
    outline: 'none',
    minWidth: '150px',
  },
  button: {
    padding: '10px 16px',
    fontSize: '14px',
    fontWeight: '500',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
  },
  primaryButton: {
    backgroundColor: '#3b82f6',
    color: '#fff',
    border: 'none',
  },
  primaryButtonHover: {
    backgroundColor: '#2563eb',
  },
  secondaryButton: {
    backgroundColor: '#fff',
    color: '#444',
    border: '1px solid #ddd',
  },
  secondaryButtonHover: {
    backgroundColor: '#f3f4f6',
  },
  dangerButton: {
    backgroundColor: '#ef4444',
    color: '#fff',
    border: 'none',
  },
  dangerButtonHover: {
    backgroundColor: '#dc2626',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
    fontSize: '14px',
  },
  tableHeader: {
    borderBottom: '2px solid #eaeaea',
    color: '#6b7280',
    fontWeight: '600',
    padding: '12px 16px',
    textTransform: 'uppercase',
    fontSize: '12px',
    letterSpacing: '0.05em',
  },
  tableHeaderSortable: {
    cursor: 'pointer',
    userSelect: 'none',
  },
  tableHeaderSortableActive: {
    color: '#3b82f6',
  },
  tableRow: {
    borderBottom: '1px solid #eaeaea',
    transition: 'background-color 0.2s',
  },
  tableRowHover: {
    backgroundColor: '#f9fafb',
  },
  tableCell: {
    padding: '16px',
    verticalAlign: 'middle',
  },
  tableCellActions: {
    padding: '12px 16px',
    textAlign: 'right',
  },
  badge: {
    padding: '4px 8px',
    borderRadius: '9999px',
    fontSize: '12px',
    fontWeight: '500',
    display: 'inline-block',
  },
  badgeLow: {
    backgroundColor: '#fee2e2',
    color: '#b91c1c',
  },
  badgeMedium: {
    backgroundColor: '#fef3c7',
    color: '#92400e',
  },
  badgeHigh: {
    backgroundColor: '#ecfdf5',
    color: '#047857',
  },
  actionButton: {
    padding: '6px',
    borderRadius: '4px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#6b7280',
    marginLeft: '8px',
  },
  editButton: {
    color: '#3b82f6',
  },
  deleteButton: {
    color: '#ef4444',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '24px',
    flexWrap: 'wrap',
  },
  paginationInfo: {
    color: '#6b7280',
    fontSize: '14px',
  },
  paginationButtons: {
    display: 'flex',
    gap: '8px',
  },
  paginationButton: {
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    backgroundColor: '#fff',
    color: '#374151',
    cursor: 'pointer',
    fontSize: '14px',
    transition: 'all 0.2s',
  },
  paginationButtonActive: {
    backgroundColor: '#3b82f6',
    color: '#fff',
    borderColor: '#3b82f6',
  },
  paginationButtonDisabled: {
    opacity: '0.5',
    cursor: 'not-allowed',
  },
  noResults: {
    textAlign: 'center',
    padding: '48px 0',
    color: '#6b7280',
  },
  loadingOverlay: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '48px 0',
  },
  loadingSpinner: {
    animation: 'spin 1s linear infinite',
    display: 'inline-block',
  },
  '@keyframes spin': {
    '0%': { transform: 'rotate(0deg)' },
    '100%': { transform: 'rotate(360deg)' },
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '24px',
    width: '90%',
    maxWidth: '500px',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    paddingBottom: '16px',
    borderBottom: '1px solid #eaeaea',
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#111827',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '24px',
    paddingTop: '16px',
    borderTop: '1px solid #eaeaea',
  },
};

