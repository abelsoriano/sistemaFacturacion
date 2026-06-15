export const PDF_DEFAULT_CONFIG = {
  paperSize: [80, 297],
  unit: 'mm',
  pageWidth: 80,
  margin: 5,
  currencySymbol: '$',
  filename: 'ticket.pdf',
  company: {
    name: 'Nombre de la Empresa',
    address: 'Dirección de la Empresa',
    phone: 'Tel: Teléfono de la Empresa ',
    city: 'Santo Domingo Rep. Dom.',
  },
  showCompanyHeader: true,
  showInvoiceHeader: true,
  showDate: true,
  dateLocale: 'es-ES',
  dateOptions: {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  },
  showClientName: true,
  clientNameLabel: 'Cliente',
  showNotes: true,
  notesLabel: 'Notas',
  dateLabel: 'Fecha',
  showTotals: true,
  showCashChange: true,
  totalLabel: 'Total',
  cashLabel: 'Efectivo',
  changeLabel: 'Cambio',
  invoiceNumberLabel: 'Factura N°',
  tableHeaders: {
    quantity: 'Cant',
    description: 'Descripción',
    price: 'Precio',
    total: 'Total',
  },
  footerLines: ['¡Gracias por su compra!', 'Vuelva pronto'],
  descriptionMaxWidth: 25,
  lineSpacing: 5,
  titleFontSize: 12,
  bodyFontSize: 8,
};

export const PDF_CONFIG_STORAGE_KEY = 'invoicePdfConfig';

export const getSavedPDFConfig = () => {
  try {
    const stored = localStorage.getItem(PDF_CONFIG_STORAGE_KEY);
    if (!stored) return {};
    const parsed = JSON.parse(stored);
    return typeof parsed === 'object' && parsed !== null ? parsed : {};
  } catch (error) {
    console.warn('Error leyendo configuración PDF:', error);
    return {};
  }
};

export const savePDFConfig = (config) => {
  try {
    localStorage.setItem(PDF_CONFIG_STORAGE_KEY, JSON.stringify(config));
  } catch (error) {
    console.error('Error guardando configuración PDF:', error);
  }
};

export const resetPDFConfig = () => {
  localStorage.removeItem(PDF_CONFIG_STORAGE_KEY);
};

export const formatMoney = (value, symbol = '$') => {
  const amount = Number(value ?? 0);
  return `${symbol}${Number.isNaN(amount) ? '0.00' : amount.toFixed(2)}`;
};
