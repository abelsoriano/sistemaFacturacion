"""Canonical row locking for concurrent inventory mutations."""

from __future__ import annotations

from collections.abc import Iterable

from facturacion.models import Company, Product


def lock_products_for_inventory(
    product_ids: Iterable[int],
    *,
    company: Company | None = None,
) -> dict[int, Product]:
    """Lock inventory products in ascending primary-key order.

    Every stock-changing transaction must acquire its complete product set
    through this helper before it validates or updates stock.  The explicit
    ordering gives PostgreSQL one lock acquisition order across invoice and
    credit-note flows.
    """
    ids = sorted({int(product_id) for product_id in product_ids})
    if not ids:
        return {}

    queryset = Product.objects.select_for_update().filter(pk__in=ids).order_by("pk")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {product.pk: product for product in queryset}
