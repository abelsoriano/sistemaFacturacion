import {
  BarChart3,
  Boxes,
  Building2,
  ClipboardList,
  FileText,
  LayoutDashboard,
  Package,
  Receipt,
  ReceiptText,
  Settings,
  ShoppingCart,
  UserCog,
  Users,
  Wrench,
  MoreHorizontal,
  FileCheck2,
} from 'lucide-react';

import { ROUTE_PERMISSIONS } from './utils/permissions';

export const navGroups = [
  {
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        route: '/home',
        icon: LayoutDashboard,
        permissions: [],
        aliases: ['/dashboard'],
      },
    ],
  },
  {
    label: 'Comercial',
    items: [
      {
        id: 'sales',
        label: 'Ventas',
        route: '/salesList',
        icon: ShoppingCart,
        permissions: ROUTE_PERMISSIONS['/salesList'],
        aliases: ['/Fastsales', '/sales'],
      },
      {
        id: 'invoices',
        label: 'Facturas',
        route: '/invoice-list',
        icon: ReceiptText,
        permissions: ROUTE_PERMISSIONS['/invoice-list'],
        aliases: ['/create-invoice', '/edit-invoice', '/invoices'],
      },
      {
        id: 'quotations',
        label: 'Cotizaciones',
        route: '/quotations',
        icon: FileText,
        permissions: ROUTE_PERMISSIONS['/quotations'],
        aliases: ['/quotations/new'],
      },
      {
        id: 'credit-notes',
        label: 'Notas de crédito',
        route: '/credit-notes',
        icon: Receipt,
        permissions: ROUTE_PERMISSIONS['/ecf'],
      },
    ],
  },
  {
    label: 'Operaciones',
    items: [
      {
        id: 'clients',
        label: 'Clientes',
        route: '/clients',
        icon: Users,
        permissions: ROUTE_PERMISSIONS['/clients'],
        aliases: ['/clients/new', '/clients/'],
      },
      {
        id: 'inventory',
        label: 'Inventario',
        route: '/productsList',
        icon: Package,
        permissions: ROUTE_PERMISSIONS['/productsList'],
        aliases: ['/productsForm', '/products/', '/categoriaList', '/categoriesForm'],
      },
      {
        id: 'warehouse',
        label: 'Almacén',
        route: '/list-item',
        icon: Boxes,
        permissions: ROUTE_PERMISSIONS['/list-item'],
        aliases: ['/register-item'],
      },
      {
        id: 'labour',
        label: 'Venta a Crédito',
        route: '/labour-list',
        icon: Wrench,
        permissions: ROUTE_PERMISSIONS['/labour-list'],
        aliases: ['/register-labour'],
      },
      {
        id: 'assets',
        label: 'Activos',
        route: '/assetsManager',
        icon: ClipboardList,
        permissions: ROUTE_PERMISSIONS['/assetsManager'],
        aliases: ['/assetsForm', '/assets/edit'],
      },
      {
        id: 'ecf',
        label: 'e-CF / DGII',
        route: '/ecf',
        icon: Receipt,
        permissions: ROUTE_PERMISSIONS['/ecf'],
      },
      {
        id: 'reports',
        label: 'Reportes',
        route: '/sales-reports',
        icon: BarChart3,
        permissions: ROUTE_PERMISSIONS['/sales-reports'],
        aliases: ['/low-stock-report', '/dashboard'],
      },
    ],
  },
  {
    label: 'Empresa',
    items: [
      {
        id: 'team',
        label: 'Equipo',
        route: '/company/team',
        icon: UserCog,
        permissions: [],
        aliases: ['/company/team'],
      },
      {
        id: 'company',
        label: 'Empresa',
        route: '/company',
        icon: Building2,
        permissions: [],
      },
      {
        id: 'dgii-certification',
        label: 'Certificación DGII',
        route: '/company/dgii-certification',
        icon: FileCheck2,
        permissions: [],
      },
      {
        id: 'settings',
        label: 'Configuración',
        route: '/pdf-config',
        icon: Settings,
        permissions: ROUTE_PERMISSIONS['/pdf-config'],
      },
    ],
  },
];

export const bottomNavItems = [
  navGroups[0].items[0],
  navGroups[1].items[1],
  {
    id: 'new-sale',
    label: 'POS',
    route: '/Fastsales',
    icon: ShoppingCart,
    permissions: ROUTE_PERMISSIONS['/Fastsales'],
  },
  navGroups[2].items[0],
  {
    id: 'more',
    label: 'Más',
    route: null,
    icon: MoreHorizontal,
    permissions: [],
  },
];

const bottomPrimaryIds = new Set(bottomNavItems.map((item) => item.id));

export const bottomMoreItems = navGroups.flatMap((group) => (
  group.items.filter((item) => !bottomPrimaryIds.has(item.id))
));

export function isNavItemActive(item, currentPath) {
  const itemPath = item.route || '';
  const pathname = (currentPath || '').split('?')[0];
  if (pathname === itemPath) return true;
  return (item.aliases || []).some((alias) => {
    const aliasPath = alias || '';
    return pathname === aliasPath || pathname.startsWith(`${aliasPath}/`);
  });
}
