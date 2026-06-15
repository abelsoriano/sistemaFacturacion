import React from 'react';
import { Document, Page, Text, View, StyleSheet} from '@react-pdf/renderer';
import { Link } from 'react-router-dom';
import { IconExcel, IconInvoice, IconReport, IconBox } from './Icons';

const styles = StyleSheet.create({
  page: {
    padding: 30,
    fontSize: 12
  },
  header: {
    marginBottom: 20,
    textAlign: 'center'
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10
  },
  table: {
    display: "table",
    width: "auto",
    borderStyle: "solid",
    borderWidth: 1,
    borderRightWidth: 0,
    borderBottomWidth: 0
  },
  tableRow: {
    flexDirection: "row"
  },
  tableColHeader: {
    width: "20%",
    borderStyle: "solid",
    borderWidth: 1,
    borderLeftWidth: 0,
    borderTopWidth: 0,
    backgroundColor: '#f0f0f0',
    padding: 5
  },
  tableCol: {
    width: "20%",
    borderStyle: "solid",
    borderWidth: 1,
    borderLeftWidth: 0,
    borderTopWidth: 0,
    padding: 5
  },
  headerText: {
    fontWeight: 'bold',
    textAlign: 'center'
  },
  footer: {
    marginTop: 20,
    textAlign: 'right'
  }
});

// Deprecated: kept only for legacy /sales-reports compatibility.
// Official commercial reporting now uses Invoice data.
const SalesPDFReport = ({ sales, documentMode = false } = {}) => {
  const rows = Array.isArray(sales) ? sales : [];
  const shouldRenderDocument = documentMode || Array.isArray(sales);
  const rowDate = (row) => row.created_at || row.date;
  const rowCustomer = (row) => row.client_name || row.customer || 'Consumidor Final';
  const rowNumber = (row) => row.invoice_number || row.id;
  const totalFacturas = rows.reduce((acc, sale) => acc + parseFloat(sale.total || 0), 0);
  const totalProductos = rows.reduce((acc, sale) => acc + (sale.details?.length || 0), 0);

  if (shouldRenderDocument) {
    return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.header}>
          <Text style={styles.title}>Reporte de facturas</Text>
          <Text>Incluye documentos pendientes de cobro si forman parte de la fuente enviada.</Text>
          <Text>Fecha de generación: {new Date().toLocaleDateString()}</Text>
        </View>

        <View style={styles.table}>
          {/* Encabezados */}
          <View style={styles.tableRow}>
            <View style={styles.tableColHeader}>
              <Text style={styles.headerText}>ID</Text>
            </View>
            <View style={styles.tableColHeader}>
              <Text style={styles.headerText}>Mecánico</Text>
            </View>
            <View style={styles.tableColHeader}>
              <Text style={styles.headerText}>Fecha</Text>
            </View>
            <View style={styles.tableColHeader}>
              <Text style={styles.headerText}>Total</Text>
            </View>
            <View style={styles.tableColHeader}>
              <Text style={styles.headerText}>Productos</Text>
            </View>
          </View>

          {/* Datos */}
          {rows.map((sale) => (
            <View style={styles.tableRow} key={sale.id}>
              <View style={styles.tableCol}>
                <Text>{rowNumber(sale)}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>{rowCustomer(sale)}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>{rowDate(sale) ? new Date(rowDate(sale)).toLocaleDateString() : 'n/a'}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>${parseFloat(sale.total || 0).toFixed(2)}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>{sale.details?.length || 0}</Text>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.footer}>
          <Text>Total facturas: ${totalFacturas.toFixed(2)}</Text>
          <Text>Total productos facturados: {totalProductos}</Text>
          <Text>Cantidad de facturas: {rows.length}</Text>
        </View>
      </Page>
    </Document>
    );
  }

  return (
    <>
      <style>{`
        .sr-page {
          min-height: 100vh;
          padding: 1.5rem;
          background: #f6f7fb;
        }
        .sr-wrap {
          max-width: 1120px;
          margin: 0 auto;
        }
        .sr-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          flex-wrap: wrap;
          background: #ffffff;
          border: 1px solid #e6e8f0;
          border-radius: 8px;
          padding: 1.25rem;
          box-shadow: 0 12px 28px rgba(27, 26, 46, 0.06);
        }
        .sr-title {
          display: flex;
          align-items: center;
          gap: 0.85rem;
        }
        .sr-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 42px;
          height: 42px;
          border-radius: 8px;
          background: #EEEDFE;
          color: #6C63FF;
        }
        .sr-title h1 {
          margin: 0;
          color: #1B1A2E;
          font-size: 1.45rem;
        }
        .sr-title p {
          margin: 0.25rem 0 0;
          color: #717184;
          font-size: 0.9rem;
        }
        .sr-actions {
          display: flex;
          gap: 0.75rem;
          flex-wrap: wrap;
        }
        .sr-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          border: 1px solid #dfe3ee;
          border-radius: 8px;
          padding: 0.68rem 0.95rem;
          color: #303044;
          background: #ffffff;
          font-weight: 700;
          text-decoration: none;
        }
        .sr-btn.primary {
          color: #ffffff;
          background: #6C63FF;
          border-color: #6C63FF;
          box-shadow: 0 10px 18px rgba(108, 99, 255, 0.18);
        }
        .sr-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 1rem;
          margin-top: 1rem;
        }
        .sr-card {
          background: #ffffff;
          border: 1px solid #e6e8f0;
          border-radius: 8px;
          padding: 1rem;
          box-shadow: 0 8px 20px rgba(27, 26, 46, 0.04);
        }
        .sr-card h2 {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin: 0 0 0.5rem;
          color: #1B1A2E;
          font-size: 1rem;
        }
        .sr-card p {
          margin: 0 0 1rem;
          color: #717184;
          font-size: 0.88rem;
          line-height: 1.45;
        }
        .sr-note {
          margin-top: 1rem;
          padding: 0.85rem 1rem;
          border: 1px solid #dbeafe;
          border-radius: 8px;
          background: #eff6ff;
          color: #1d4ed8;
          font-size: 0.88rem;
        }
        @media (max-width: 820px) {
          .sr-page { padding: 1rem; }
          .sr-header,
          .sr-actions {
            flex-direction: column;
            align-items: stretch;
          }
          .sr-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
      <main className="sr-page">
        <div className="sr-wrap">
          <section className="sr-header">
            <div className="sr-title">
              <span className="sr-icon"><IconReport /></span>
              <div>
                <h1>Reportes comerciales</h1>
                <p>Consulta ventas cobradas, facturas y reportes operativos desde las fuentes oficiales actuales.</p>
              </div>
            </div>
            <div className="sr-actions">
              <Link className="sr-btn primary" to="/salesList"><IconExcel /> Ventas</Link>
              <Link className="sr-btn" to="/invoice-list"><IconInvoice /> Facturas</Link>
            </div>
          </section>

          <section className="sr-grid">
            <div className="sr-card">
              <h2><IconExcel /> Ventas cobradas</h2>
              <p>Listado comercial basado en facturas. Las métricas separan cobrado y pendiente de cobro.</p>
              <Link className="sr-btn" to="/salesList">Abrir ventas</Link>
            </div>
            <div className="sr-card">
              <h2><IconInvoice /> Facturas</h2>
              <p>Consulta documentos comerciales con estados fiscal y técnico separados.</p>
              <Link className="sr-btn" to="/invoice-list">Abrir facturas</Link>
            </div>
            <div className="sr-card">
              <h2><IconBox /> Bajo stock</h2>
              <p>Reporte operativo de inventario con exportación Excel y PDF.</p>
              <Link className="sr-btn" to="/low-stock-report">Abrir bajo stock</Link>
            </div>
          </section>

          <div className="sr-note">
            El generador PDF legacy se conserva solo para compatibilidad interna. La fuente comercial oficial es Invoice.
          </div>
        </div>
      </main>
    </>
  );
};

export default SalesPDFReport;
