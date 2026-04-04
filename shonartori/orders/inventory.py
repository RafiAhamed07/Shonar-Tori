"""Stock commits/restores tied to orders (idempotent)."""
from django.db import transaction
from django.db.models import F

from products.models import Product


class InsufficientStock(Exception):
    def __init__(self, product_name: str, available: int, requested: int):
        self.product_name = product_name
        self.available = available
        self.requested = requested
        super().__init__(
            f"{product_name}: need {requested}, only {available} in stock."
        )


def assert_cart_has_stock(cart) -> None:
    if not cart:
        raise InsufficientStock("Cart", 0, 0)
    for item in cart.cart_items.select_related("product"):
        if item.product.stock < item.quantity:
            raise InsufficientStock(
                item.product.product_name,
                item.product.stock,
                item.quantity,
            )


@transaction.atomic
def commit_inventory_for_order(order) -> None:
    """Deduct stock once per order. Safe to call again (no-op)."""
    from .models import Order

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.inventory_committed:
        return
    items = list(order.order_items.select_related("product"))
    for item in items:
        product = Product.objects.select_for_update().get(pk=item.product_id)
        if product.stock < item.quantity:
            raise InsufficientStock(
                product.product_name,
                product.stock,
                item.quantity,
            )
    for item in items:
        Product.objects.filter(pk=item.product_id).update(stock=F("stock") - item.quantity)
    order.inventory_committed = True
    order.save(update_fields=["inventory_committed"])


@transaction.atomic
def restore_inventory_for_order(order) -> None:
    """Put stock back (e.g. cancelled pending order that already committed inventory)."""
    from .models import Order

    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.inventory_committed:
        return
    for item in order.order_items.all():
        Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
    order.inventory_committed = False
    order.save(update_fields=["inventory_committed"])
