import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Spin, DatePicker, Select, Button } from 'antd';
import {
  ShoppingCartOutlined,
  DollarOutlined,
  StockOutlined,
  TagOutlined,
  HomeOutlined
} from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';
import moment from 'moment';
import styles from '../css/Dashboard.module.css';

const { RangePicker } = DatePicker;
const { Option } = Select;

const Dashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState([moment().startOf('month'), moment().endOf('month')]);
  const [timeFrame, setTimeFrame] = useState('month');
  const [dashboardData, setDashboardData] = useState({
    salesSummary: {},
    topProducts: [],
    salesByCategory: [],
    recentSales: [],
    inventoryStatus: {},
    salesTrend: []
  });

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [startDate, endDate] = dateRange;
      const params = {
        start_date: startDate.format('YYYY-MM-DD'),
        end_date: endDate.format('YYYY-MM-DD'),
        time_frame: timeFrame
      };

      const response = await api.get('/dashboard/', { params });
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [dateRange, timeFrame]);

  const handleDateChange = (dates) => {
    if (dates) {
      setDateRange(dates);
    }
  };

  const handleTimeFrameChange = (value) => {
    setTimeFrame(value);
  };

  const goToHome = () => {
    navigate('/home');
  };

  return (
    <div className={styles.dashboardContainer}>
      <div className={styles.dashboardHeader}>
        <div className={styles.headerLeft}>
          <h1>Panel de Control</h1>
          <Button 
            type="primary" 
            icon={<HomeOutlined />} 
            onClick={goToHome}
            className={styles.homeButton}
          >
            Ir al Inicio
          </Button>
        </div>
        <div className={styles.dashboardControls}>
          <RangePicker
            value={dateRange}
            onChange={handleDateChange}
            style={{ marginRight: 16 }}
          />
          <Select
            defaultValue="month"
            style={{ width: 120 }}
            onChange={handleTimeFrameChange}
          >
            <Option value="day">Diario</Option>
            <Option value="week">Semanal</Option>
            <Option value="month">Mensual</Option>
            <Option value="year">Anual</Option>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className={styles.loadingSpinner}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <Row gutter={16} className={styles.summaryCards}>
            <Col span={6}>
              <Card>
                <div className={styles.summaryCard}>
                  <DollarOutlined className={styles.summaryIcon} style={{ color: '#1890ff' }} />
                  <div className={styles.summaryContent}>
                    <h3>Ventas Totales</h3>
                    <p>${dashboardData.salesSummary.total_sales?.toFixed(2) || '0.00'}</p>
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <div className={styles.summaryCard}>
                  <ShoppingCartOutlined className={styles.summaryIcon} style={{ color: '#52c41a' }} />
                  <div className={styles.summaryContent}>
                    <h3>Ventas</h3>
                    <p>{dashboardData.salesSummary.sales_count || 0}</p>
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <div className={styles.summaryCard}>
                  <TagOutlined className={styles.summaryIcon} style={{ color: '#faad14' }} />
                  <div className={styles.summaryContent}>
                    <h3>Productos Vendidos</h3>
                    <p>{dashboardData.salesSummary.products_sold || 0}</p>
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <div className={styles.summaryCard}>
                  <StockOutlined className={styles.summaryIcon} style={{ color: '#f5222d' }} />
                  <div className={styles.summaryContent}>
                    <h3>Stock Bajo</h3>
                    <p>{dashboardData.inventoryStatus.low_stock_count || 0}</p>
                  </div>
                </div>
              </Card>
            </Col>
          </Row>

          {/* Charts Row 1 */}
          <Row gutter={16} className={styles.chartRow}>
            <Col span={12}>
              <Card title="Tendencia de Ventas" className={styles.chartCard}>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dashboardData.salesTrend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="sales"
                      stroke="#8884d8"
                      activeDot={{ r: 8 }}
                      name="Ventas"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Ventas por Categoría" className={styles.chartCard}>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={dashboardData.salesByCategory}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      nameKey="name"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {dashboardData.salesByCategory.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>

          {/* Charts Row 2 */}
          <Row gutter={16} className={styles.chartRow}>
            <Col span={12}>
              <Card title="Productos Más Vendidos" className={styles.chartCard}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dashboardData.topProducts}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="quantity" fill="#8884d8" name="Cantidad Vendida" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="Estado del Inventario" className={styles.chartCard}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dashboardData.inventoryStatus.categories}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="in_stock" fill="#52c41a" name="En Stock" />
                    <Bar dataKey="low_stock" fill="#faad14" name="Stock Bajo" />
                    <Bar dataKey="out_of_stock" fill="#f5222d" name="Agotado" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>

          {/* Recent Sales */}
          <Card title="Ventas Recientes" className={styles.recentSalesCard}>
            <div className={styles.recentSalesTable}>
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Cliente</th>
                    <th>Fecha</th>
                    <th>Total</th>
                    <th>Productos</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboardData.recentSales.map((sale) => (
                    <tr key={sale.id}>
                      <td>{sale.id}</td>
                      <td>{sale.customer || 'N/A'}</td>
                      <td>{moment(sale.date).format('DD/MM/YYYY HH:mm')}</td>
                      <td>${sale.total.toFixed(2)}</td>
                      <td>{sale.details_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
};

export default Dashboard;