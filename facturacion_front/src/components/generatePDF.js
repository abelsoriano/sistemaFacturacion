import jsPDF from 'jspdf';

export const generatePDF = (invoiceData) => {
  // Validar que invoiceData y invoiceData.details estén definidos
  if (!invoiceData || !invoiceData.details) {
    console.error("Datos de la factura no válidos:", invoiceData);
    alert("No se pudieron generar los detalles de la factura. Verifica los datos.");
    return;
  }

  // Crear un documento PDF con dimensiones de ticket (80mm de ancho)
  const doc = new jsPDF({
    format: [80, 297], // Ancho de 80mm (ticket estándar)
    unit: 'mm'
  });

  // Configuración inicial
  const pageWidth = 80;
  const margin = 5;
  const contentWidth = pageWidth - (margin * 2);
  let yPos = margin;

  // Función helper para centrar texto
  const centerText = (text, y) => {
    const textWidth = doc.getStringUnitWidth(text) * doc.internal.getFontSize() / doc.internal.scaleFactor;
    const textOffset = (pageWidth - textWidth) / 2;
    doc.text(text, textOffset, y);
  };

  // Nombre de la empresa
  doc.setFontSize(12);
  doc.setFont(undefined, 'bold');
  centerText("REPUESTOS BEBE", yPos + 5);
  
  // Dirección
  yPos += 10;
  doc.setFontSize(8);
  doc.setFont(undefined, 'normal');
  centerText("San Felipe de Villa Mella, C/Liecy No.88 ", yPos);
  yPos += 4;
  centerText("Tel: (809) 986-6178", yPos);
  yPos += 4;
  centerText("Santo Domingo Rep. Dom.", yPos);

  // Línea separadora
  yPos += 5;
  doc.line(margin, yPos, pageWidth - margin, yPos);

  // Número de factura y fecha
  yPos += 5;
  doc.setFontSize(8);
  const currentDate = new Date().toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
  doc.text(`Factura N°: ${invoiceData.id || 'N/A'}`, margin, yPos); // Usar 'N/A' si no hay ID
  yPos += 4;
  doc.text(`Fecha: ${currentDate}`, margin, yPos);

  // Línea separadora
  yPos += 5;
  doc.line(margin, yPos, pageWidth - margin, yPos);

  // Encabezados de la tabla
  yPos += 5;
  doc.setFont(undefined, 'bold');
  doc.text("Cant", margin, yPos);
  doc.text('Descripcion', margin + 10, yPos);
  doc.text("Precio", margin + 40, yPos);
  doc.text("Total", margin + 60, yPos);

  // Detalles de productos
  doc.setFont(undefined, 'normal');
  invoiceData.details.forEach((item) => {
    yPos += 5;
    doc.text(`${item.quantity}`, margin, yPos)
    doc.text(`${item.products}`, margin + 10, yPos);
    doc.text(`$${item.price}`, margin + 40, yPos);
    doc.text(`$${item.subtotal}`, margin + 60, yPos);
  });
 
  // Línea separadora
  yPos += 5;
  doc.line(margin, yPos, pageWidth - margin, yPos);

  // Totales
  yPos += 5;
  doc.setFont(undefined, 'bold');
  doc.text("Total:", margin, yPos);
  doc.text(`$${invoiceData.total}`, margin + 50, yPos);
  
  yPos += 5;
  doc.setFont(undefined, 'normal');
  doc.text("Efectivo:", margin, yPos);
  doc.text(`$${invoiceData.cash_received}`, margin + 50, yPos);
  
  yPos += 5;
  doc.text("Cambio:", margin, yPos);
  doc.text(`$${invoiceData.change}`, margin + 50, yPos);

  // Mensaje final
  yPos += 10;
  doc.setFontSize(8);
  centerText("¡Gracias por su compra!", yPos);
  yPos += 5;
  centerText("Vuelva pronto", yPos);

  // Guardar el PDF
  doc.save('ticket.pdf');
};