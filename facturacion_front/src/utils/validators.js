export const RNC_MESSAGE = 'El RNC/Cedula debe contener solo numeros y tener 9 u 11 digitos.';
export const PHONE_MESSAGE = 'El telefono solo puede contener numeros, espacios, guiones, parentesis y +.';
export const PHONE_MAX_LENGTH = 20;

export function onlyDigits(value = '') {
  return String(value || '').replace(/\D/g, '');
}

export function validateRnc(value, { required = false, label = 'RNC/Cedula' } = {}) {
  const raw = String(value || '').trim();
  if (!raw) {
    return required ? `${label} es obligatorio.` : '';
  }
  if (!/^\d+$/.test(raw)) {
    return `${label} solo debe contener numeros.`;
  }
  if (![9, 11].includes(raw.length)) {
    return `${label} debe tener 9 u 11 digitos.`;
  }
  return '';
}

export function normalizeRncInput(value = '') {
  return onlyDigits(value).slice(0, 11);
}

export function validatePhone(value, { label = 'Telefono' } = {}) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (!/^[0-9\s()+-]+$/.test(raw)) {
    return `${label} solo puede contener numeros, espacios, guiones, parentesis y +.`;
  }
  if (raw.length > PHONE_MAX_LENGTH) {
    return `${label} no debe exceder ${PHONE_MAX_LENGTH} caracteres.`;
  }
  return '';
}
