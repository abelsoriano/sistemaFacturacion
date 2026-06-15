import Swal from 'sweetalert2';

const toast = Swal.mixin({
  toast: true,
  position: 'top-end',
  showConfirmButton: false,
  timer: 3200,
  timerProgressBar: true,
});

const showToast = (icon, title, text) => toast.fire({
  icon,
  title: title || '',
  text: text || '',
});

export const notify = {
  success: (title, text) => showToast('success', title || 'Listo', text),
  error: (title, text) => showToast('error', title || 'No se pudo completar', text),
  warning: (title, text) => showToast('warning', title || 'Atención', text),
  info: (title, text) => showToast('info', title || 'Información', text),
};

export default notify;
