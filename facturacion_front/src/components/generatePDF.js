import jsPDF from 'jspdf';
import { PDF_DEFAULT_CONFIG, formatMoney, getSavedPDFConfig } from '../utils/pdfConfig';

const mergeConfig = (baseConfig, overrideConfig = {}) => ({
  ...baseConfig,
  ...overrideConfig,
  company: { ...baseConfig.company, ...(overrideConfig.company || {}) },
  tableHeaders: { ...baseConfig.tableHeaders, ...(overrideConfig.tableHeaders || {}) },
});
 
export const generatePDF = (invoiceData, config = {}) => {
  const savedConfig = getSavedPDFConfig();
  const settings = mergeConfig(mergeConfig(PDF_DEFAULT_CONFIG, savedConfig), config);
  const details = invoiceData?.details?.length ? invoiceData.details : invoiceData?.items || invoiceData?.products || [];

  if (!invoiceData || !details || !details.length) {
    console.error('Datos de la factura no válidos:', invoiceData);
    alert('No se pudieron generar los detalles de la factura. Verifica los datos.');
    return;
  }

  const doc = new jsPDF({
    format: settings.paperSize,
    unit: settings.unit,
  });

  const pageWidth = settings.pageWidth;
  const margin = settings.margin;
  let yPos = margin;

  const centerText = (text, y) => {
    const textWidth = doc.getStringUnitWidth(text) * doc.internal.getFontSize() / doc.internal.scaleFactor;
    const textOffset = (pageWidth - textWidth) / 2;
    doc.text(text, textOffset, y);
  };

  const addSeparator = () => {
    yPos += settings.lineSpacing;
    doc.line(margin, yPos, pageWidth - margin, yPos);
  };

  const invoiceNumber = invoiceData.invoice_number || invoiceData.id || 'N/A';
  const invoiceDate = invoiceData.date ? new Date(invoiceData.date) : new Date();
  const currentDate = invoiceDate.toLocaleDateString(settings.dateLocale, settings.dateOptions);

  doc.setFontSize(settings.titleFontSize);
  doc.setFont(undefined, 'bold');

  if (settings.showCompanyHeader) {
    centerText(settings.company.name, yPos + 5);
    yPos += settings.lineSpacing * 2;
    doc.setFontSize(settings.bodyFontSize);
    doc.setFont(undefined, 'normal');
    centerText(settings.company.address, yPos);
    yPos += settings.lineSpacing;
    centerText(settings.company.phone, yPos);
    yPos += settings.lineSpacing;
    centerText(settings.company.city, yPos);
    yPos += settings.lineSpacing;
    addSeparator();
  }

  if (settings.showInvoiceHeader) {
    yPos += settings.lineSpacing;
    doc.setFontSize(settings.bodyFontSize);
    doc.setFont(undefined, 'bold');
    doc.text(`${settings.invoiceNumberLabel}: ${invoiceNumber}`, margin, yPos);
    yPos += settings.lineSpacing;

    if (settings.showDate) {
      doc.setFont(undefined, 'normal');
      doc.text(`${settings.dateLabel}: ${currentDate}`, margin, yPos);
      yPos += settings.lineSpacing;
    }

    if (settings.showClientName && invoiceData.clientName) {
      doc.setFont(undefined, 'normal');
      doc.text(`${settings.clientNameLabel}: ${invoiceData.clientName}`, margin, yPos);
      yPos += settings.lineSpacing;
    }

    addSeparator();
  }

  yPos += settings.lineSpacing;
  doc.setFont(undefined, 'bold');
  doc.text(settings.tableHeaders.quantity, margin, yPos);
  doc.text(settings.tableHeaders.description, margin + 12, yPos);
  doc.text(settings.tableHeaders.price, margin + 40, yPos);
  doc.text(settings.tableHeaders.total, margin + 60, yPos);

  doc.setFont(undefined, 'normal');
  details.forEach((item) => {
    yPos += settings.lineSpacing;
    const description = item.description || item.product_name || item.product || item.name || '';
    const subtotal = item.subtotal ?? Number(item.quantity || 0) * Number(item.price || 0);
    const descriptionLines = doc.splitTextToSize(description, settings.descriptionMaxWidth);

    doc.text(`${item.quantity || 0}`, margin, yPos);
    doc.text(descriptionLines, margin + 12, yPos);
    doc.text(formatMoney(item.price, settings.currencySymbol), margin + 40, yPos);
    doc.text(formatMoney(subtotal, settings.currencySymbol), margin + 60, yPos);

    yPos += settings.lineSpacing * (descriptionLines.length - 1);
  });

  addSeparator();
  yPos += settings.lineSpacing;
  doc.setFont(undefined, 'bold');
  doc.text(`${settings.totalLabel}:`, margin, yPos);
  doc.text(formatMoney(invoiceData.total, settings.currencySymbol), margin + 50, yPos);

  if (settings.showCashChange) {
    yPos += settings.lineSpacing;
    doc.setFont(undefined, 'normal');
    doc.text(`${settings.cashLabel}:`, margin, yPos);
    doc.text(formatMoney(invoiceData.cash_received, settings.currencySymbol), margin + 50, yPos);
    yPos += settings.lineSpacing;
    doc.text(`${settings.changeLabel}:`, margin, yPos);
    doc.text(formatMoney(invoiceData.change, settings.currencySymbol), margin + 50, yPos);
  }

  if (settings.showNotes && invoiceData.notes) {
    yPos += settings.lineSpacing;
    doc.setFont(undefined, 'normal');
    const wrappedNotes = doc.splitTextToSize(invoiceData.notes, pageWidth - margin * 2);
    doc.text(`${settings.notesLabel}:`, margin, yPos);
    yPos += settings.lineSpacing;
    doc.text(wrappedNotes, margin, yPos);
    yPos += settings.lineSpacing * (wrappedNotes.length - 1);
  }

  if (settings.footerLines?.length) {
    yPos += settings.lineSpacing * 2;
    doc.setFontSize(settings.bodyFontSize);
    doc.setFont(undefined, 'normal');
    settings.footerLines.forEach((line) => {
      centerText(line, yPos);
      yPos += settings.lineSpacing;
    });
  }

  doc.save(settings.filename);
};
