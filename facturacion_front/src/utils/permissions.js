export const FINANCIAL_TOTALS_PERMISSION = 'facturacion.view_financial_totals';
export const LEGACY_SALE_TOTALS_PERMISSION = 'facturacion.view_sale_totals';
export const FINANCIAL_TOTALS_PERMISSIONS = [
  FINANCIAL_TOTALS_PERMISSION,
  LEGACY_SALE_TOTALS_PERMISSION,
];
export const SALE_TOTALS_PERMISSION = LEGACY_SALE_TOTALS_PERMISSION;

export const ROUTE_PERMISSIONS = {
  '/dashboard': ['facturacion.view_invoice', 'facturacion.view_product'],
  '/categoriesForm': ['facturacion.add_category'],
  '/categoriaList': ['facturacion.view_category'],
  '/productsList': ['facturacion.view_product'],
  '/productsForm': ['facturacion.add_product'],
  '/Fastsales': ['facturacion.add_invoice'],
  '/salesList': ['facturacion.view_invoice'],
  '/create-invoice': ['facturacion.add_invoice'],
  '/invoice-list': ['facturacion.view_invoice'],
  '/quotations': ['facturacion.view_quotation'],
  '/quotations/new': ['facturacion.add_quotation'],
  '/register-item': ['facturacion.add_almacen'],
  '/list-item': ['facturacion.view_almacen'],
  '/register-labour': ['facturacion.add_labour'],
  '/labour-list': ['facturacion.view_labour'],
  '/sales-reports': ['facturacion.view_invoice'],
  '/low-stock-report': ['facturacion.view_product'],
  '/assetsManager': ['facturacion.view_asset'],
  '/assetsForm': ['facturacion.add_asset'],
  '/pdf-config': [],
  '/ecf': ['facturacion.view_electronicfiscaldocument'],
  '/clients': ['facturacion.view_client'],
  '/clients/new': ['facturacion.add_client'],
  '/users': ['auth.view_user'],
  '/users/new': ['auth.add_user'],
  '/groups': ['auth.view_group'],
  '/groups/new': ['auth.add_group'],
};

export function userHasPermissions(user, permissions = []) {
  if (!permissions.length) return true;
  if (!user) return false;
  if (user.is_superuser) return true;
  if (permissions.some(permission => permission.startsWith('auth.')) && !user.is_staff) return false;

  const userPermissions = new Set(user.permissions || []);
  return permissions.every(permission => userPermissions.has(permission));
}

export function userHasAnyPermission(user, permissions = []) {
  if (!permissions.length) return true;
  if (!user) return false;
  if (user.is_superuser) return true;
  const allowedPermissions = user.is_staff
    ? permissions
    : permissions.filter(permission => !permission.startsWith('auth.'));
  if (!allowedPermissions.length) return false;

  const userPermissions = new Set(user.permissions || []);
  return allowedPermissions.some(permission => userPermissions.has(permission));
}

export function getPermissionsForRoute(pathname) {
  if (pathname.startsWith('/categoriesForm/')) return ['facturacion.change_category'];
  if (pathname.startsWith('/productsForm/')) return ['facturacion.change_product'];
  if (pathname.startsWith('/products/') && pathname.endsWith('/history')) return ['facturacion.view_product'];
  if (pathname.startsWith('/invoices/')) return ['facturacion.view_invoice'];
  if (pathname.startsWith('/quotations/') && pathname.endsWith('/edit')) return ['facturacion.change_quotation'];
  if (pathname.startsWith('/register-item/')) return ['facturacion.change_almacen'];
  if (pathname.startsWith('/register-labour/')) return ['facturacion.change_labour'];
  if (pathname.startsWith('/products/new')) return ['facturacion.add_product'];
  if (pathname.startsWith('/products/') && pathname.endsWith('/edit')) return ['facturacion.change_product'];
  if (pathname.startsWith('/clients/') && pathname.endsWith('/edit')) return ['facturacion.change_client'];
  if (pathname.startsWith('/users/') && pathname.endsWith('/edit')) return ['auth.change_user'];
  if (pathname.startsWith('/groups/') && pathname.endsWith('/edit')) return ['auth.change_group'];
  if (pathname.startsWith('/ecf')) return ROUTE_PERMISSIONS['/ecf'];

  return ROUTE_PERMISSIONS[pathname] || [];
}
