export const SALE_TOTALS_PERMISSION = 'facturacion.view_sale_totals';

export const ROUTE_PERMISSIONS = {
  '/dashboard': ['facturacion.view_sale', 'facturacion.view_product'],
  '/categoriesForm': ['facturacion.add_category'],
  '/categoriaList': ['facturacion.view_category'],
  '/productsList': ['facturacion.view_product'],
  '/productsForm': ['facturacion.add_product'],
  '/sales': ['facturacion.add_sale'],
  '/Fastsales': ['facturacion.add_sale'],
  '/salesList': ['facturacion.view_sale'],
  '/create-invoice': ['facturacion.add_invoice'],
  '/invoice-list': ['facturacion.view_invoice'],
  '/register-item': ['facturacion.add_almacen'],
  '/list-item': ['facturacion.view_almacen'],
  '/register-labour': ['facturacion.add_labour'],
  '/labour-list': ['facturacion.view_labour'],
  '/sales-reports': ['facturacion.view_sale'],
  '/low-stock-report': ['facturacion.view_product'],
  '/assetsManager': ['facturacion.view_asset'],
  '/assetsForm': ['facturacion.add_asset'],
  '/pdf-config': [],
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

  const userPermissions = new Set(user.permissions || []);
  return permissions.every(permission => userPermissions.has(permission));
}

export function getPermissionsForRoute(pathname) {
  if (pathname.startsWith('/categoriesForm/')) return ['facturacion.change_category'];
  if (pathname.startsWith('/productsForm/')) return ['facturacion.change_product'];
  if (pathname.startsWith('/products/') && pathname.endsWith('/history')) return ['facturacion.view_product'];
  if (pathname.startsWith('/Fastsales/')) return ['facturacion.change_sale'];
  if (pathname.startsWith('/invoices/')) return ['facturacion.view_invoice'];
  if (pathname.startsWith('/register-item/')) return ['facturacion.change_almacen'];
  if (pathname.startsWith('/register-labour/')) return ['facturacion.change_labour'];
  if (pathname.startsWith('/products/new')) return ['facturacion.add_product'];
  if (pathname.startsWith('/products/') && pathname.endsWith('/edit')) return ['facturacion.change_product'];
  if (pathname.startsWith('/clients/') && pathname.endsWith('/edit')) return ['facturacion.change_client'];
  if (pathname.startsWith('/users/') && pathname.endsWith('/edit')) return ['auth.change_user'];
  if (pathname.startsWith('/groups/') && pathname.endsWith('/edit')) return ['auth.change_group'];

  return ROUTE_PERMISSIONS[pathname] || [];
}
