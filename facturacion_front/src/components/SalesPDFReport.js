import React from 'react';
import { Document, Page, Text, View, StyleSheet, PDFViewer } from '@react-pdf/renderer';

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

const SalesPDFReport = ({ sales }) => {
  const totalVentas = sales.reduce((acc, sale) => acc + parseFloat(sale.total), 0);
  const totalProductos = sales.reduce((acc, sale) => acc + sale.details.length, 0);

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.header}>
          <Text style={styles.title}>Reporte de Ventas</Text>
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
          {sales.map((sale) => (
            <View style={styles.tableRow} key={sale.id}>
              <View style={styles.tableCol}>
                <Text>{sale.id}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>{sale.customer || 'n/a'}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>{new Date(sale.date).toLocaleDateString()}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>${parseFloat(sale.total).toFixed(2)}</Text>
              </View>
              <View style={styles.tableCol}>
                <Text>{sale.details.length}</Text>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.footer}>
          <Text>Total Ventas: ${totalVentas.toFixed(2)}</Text>
          <Text>Total Productos Vendidos: {totalProductos}</Text>
          <Text>Cantidad de Ventas: {sales.length}</Text>
        </View>
      </Page>
    </Document>
  );
};

export default SalesPDFReport;