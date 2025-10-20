import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Spin,
  DatePicker,
  Select,
  Button,
  Table,
  Input,
  Pagination,
  Tabs,
  Collapse,
  Badge,
  Statistic,
  Space,
  Tooltip
} from 'antd';
import {
  ShoppingCartOutlined,
  DollarOutlined,
  StockOutlined,
  TagOutlined,
  HomeOutlined,
  SearchOutlined,
  EyeOutlined,
  BarChartOutlined,
  PieChartOutlined,
  LineChartOutlined,
  TableOutlined
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
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';
import moment from 'moment';
import styles from '../css/Dashboard.module.css';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TabPane } = Tabs;
const { Panel } = Collapse;
const { Search } = Input;

const Dashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState([moment().startOf('month'), moment().endOf('month')]);
  const [timeFrame, setTimeFrame] = useState('month');
  const [activeTab, setActiveTab] = useState('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [dashboardData, setDashboardData] = useState({
    salesSummary: {},
    topProducts: [],
    salesByCategory: [],
    recentSales: [],
    inventoryStatus: {},
    salesTrend: []
  });

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#ff7c7c'];

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

  // Filtrar productos por búsqueda
  const filteredTopProducts = dashboardData.topProducts.filter(product =>
    product.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Configuración de columnas para la tabla de productos más vendidos
  const topProductsColumns = [
    {
      title: '#',
      dataIndex: 'rank',
      key: 'rank',
      width: 50,
      render: (_, __, index) => (
        <Badge
          count={index + 1}
          style={{
            backgroundColor: index < 3 ? '#faad14' : '#d9d9d9',
            color: index < 3 ? '#fff' : '#666'
          }}
        />
      ),
    },
    {
      title: 'Producto',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span style={{ fontWeight: '500' }}>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Cantidad',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 100,
      align: 'center',
      render: (value) => (
        <Badge count={value} style={{ backgroundColor: '#52c41a' }} />
      ),
    },
    {
      title: 'Ingresos',
      dataIndex: 'revenue',
      key: 'revenue',
      width: 120,
      align: 'right',
      render: (value) => (
        <Statistic
          value={value}
          precision={2}
          prefix="$"
          valueStyle={{ fontSize: '14px' }}
        />
      ),
    }
  ];

  // Configuración de columnas para ventas recientes
  const recentSalesColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Cliente',
      dataIndex: 'customer',
      key: 'customer',
      ellipsis: true,
      render: (text) => text || 'Cliente General',
    },
    {
      title: 'Fecha',
      dataIndex: 'date',
      key: 'date',
      width: 150,
      render: (date) => moment(date).format('DD/MM/YYYY HH:mm'),
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 100,
      align: 'right',
      render: (value) => `$${value.toFixed(2)}`,
    },
    {
      title: 'Productos',
      dataIndex: 'details_count',
      key: 'details_count',
      width: 100,
      align: 'center',
      render: (count) => (
        <Badge count={count} style={{ backgroundColor: '#1890ff' }} />
      ),
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          size="small"
          onClick={() => console.log('Ver detalles:', record.id)}
        >
          Ver
        </Button>
      ),
    }
  ];

  // Datos paginados para ventas recientes
  const paginatedSales = dashboardData.recentSales.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

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
          <Space>
            <RangePicker
              value={dateRange}
              onChange={handleDateChange}
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
          </Space>
        </div>
      </div>

      {loading ? (
        <div className={styles.loadingSpinner}>
          <Spin size="large" />
        </div>
      ) : (
        <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
          {/* Pestaña de Resumen */}
          <TabPane
            tab={
              <span>
                <BarChartOutlined />
                Resumen General
              </span>
            }
            key="overview"
          >
            {/* Summary Cards */}
            <Row gutter={[16, 16]} className={styles.summaryCards}>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="Ventas Totales"
                    value={dashboardData.salesSummary.total_sales || 0}
                    precision={2}
                    prefix={<DollarOutlined style={{ color: '#1890ff' }} />}
                    suffix="$"
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="Número de Ventas"
                    value={dashboardData.salesSummary.sales_count || 0}
                    prefix={<ShoppingCartOutlined style={{ color: '#52c41a' }} />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="Productos Vendidos"
                    value={dashboardData.salesSummary.products_sold || 0}
                    prefix={<TagOutlined style={{ color: '#faad14' }} />}
                    valueStyle={{ color: '#faad14' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic
                    title="Stock Bajo"
                    value={dashboardData.inventoryStatus.low_stock_count || 0}
                    prefix={<StockOutlined style={{ color: '#f5222d' }} />}
                    valueStyle={{ color: '#f5222d' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* Gráficos Principales */}
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} lg={12}>
                <Card title="Tendencia de Ventas" className={styles.chartCard}>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={dashboardData.salesTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="period" />
                      <YAxis />
                      <RechartsTooltip />
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
              <Col xs={24} lg={12}>
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
                      <RechartsTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
            </Row>
          </TabPane>

          {/* Pestaña de Productos */}
          <TabPane
            tab={
              <span>
                <TagOutlined />
                Productos Top
              </span>
            }
            key="products"
          >
            <Card
              title="Productos Más Vendidos"
              extra={
                <Search
                  placeholder="Buscar producto..."
                  allowClear
                  style={{ width: 250 }}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              }
            >
              <Table
                columns={topProductsColumns}
                dataSource={filteredTopProducts.map((item, index) => ({
                  ...item,
                  key: index,
                  revenue: item.quantity * (item.price || 0)
                }))}
                pagination={{
                  pageSize: 15,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) =>
                    `${range[0]}-${range[1]} de ${total} productos`,
                }}
                size="middle"
              />
            </Card>

            <Card title="Estado del Inventario" style={{ marginTop: 16 }}>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={dashboardData.inventoryStatus.categories}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <RechartsTooltip />
                  <Legend />
                  <Bar dataKey="in_stock" fill="#52c41a" name="En Stock" />
                  <Bar dataKey="low_stock" fill="#faad14" name="Stock Bajo" />
                  <Bar dataKey="out_of_stock" fill="#f5222d" name="Agotado" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </TabPane>

          {/* Pestaña de Ventas */}
          <TabPane
            tab={
              <span>
                <TableOutlined />
                Ventas Recientes
              </span>
            }
            key="sales"
          >
            <Card title="Historial de Ventas">
              <Table
                columns={recentSalesColumns}
                dataSource={dashboardData.recentSales.map((item, index) => ({
                  ...item,
                  key: index
                }))}
                pagination={{
                  current: currentPage,
                  pageSize: pageSize,
                  total: dashboardData.recentSales.length,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) =>
                    `${range[0]}-${range[1]} de ${total} ventas`,
                  onChange: (page, size) => {
                    setCurrentPage(page);
                    setPageSize(size);
                  }
                }}
                scroll={{ x: 800 }}
                size="middle"
              />
            </Card>
          </TabPane>

          {/* Pestaña de Análisis */}
          <TabPane
            tab={
              <span>
                <LineChartOutlined />
                Análisis Detallado
              </span>
            }
            key="analytics"
          >
            <Collapse defaultActiveKey={['1']} size="large">
              <Panel header="Análisis de Ventas por Tiempo" key="1">
                <Card>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={dashboardData.salesTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="period" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="sales"
                        stroke="#8884d8"
                        activeDot={{ r: 8 }}
                        name="Ventas ($)"
                        strokeWidth={3}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>
              </Panel>

              <Panel header="Distribución por Categorías" key="2">
                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="Gráfico Circular">
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={dashboardData.salesByCategory}
                            cx="50%"
                            cy="50%"
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey="value"
                            nameKey="name"
                            label={({ name, value }) => `${name}: $${value}`}
                          >
                            {dashboardData.salesByCategory.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <RechartsTooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="Gráfico de Barras">
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={dashboardData.salesByCategory}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis />
                          <RechartsTooltip />
                          <Bar dataKey="value" fill="#8884d8" />
                        </BarChart>
                      </ResponsiveContainer>
                    </Card>
                  </Col>
                </Row>
              </Panel>
            </Collapse>
          </TabPane>
        </Tabs>
      )}
    </div>
  );
};

export default Dashboard;