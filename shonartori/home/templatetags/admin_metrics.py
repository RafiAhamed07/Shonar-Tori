from django import template
from django.db.models import F, IntegerField, Sum
from django.db.models.expressions import ExpressionWrapper
from django.urls import reverse

register = template.Library()


@register.inclusion_tag("admin/partials/metrics_dashboard.html")
def shonartori_admin_metrics():
    from orders.models import Order, OrderItem
    from products.models import Product

    orders_total = Order.objects.count()
    orders_pending = Order.objects.filter(status="pending").count()
    orders_paid = Order.objects.filter(status="paid").count()
    orders_failed = Order.objects.filter(status="failed").count()

    paid_lines = OrderItem.objects.filter(order__status="paid")
    units_sold = paid_lines.aggregate(t=Sum("quantity"))["t"] or 0
    line_expr = ExpressionWrapper(
        F("price") * F("quantity"),
        output_field=IntegerField(),
    )
    revenue = paid_lines.aggregate(t=Sum(line_expr))["t"] or 0

    products_total = Product.objects.count()
    products_in_stock = Product.objects.filter(stock__gt=0).count()
    products_out = Product.objects.filter(stock=0).count()
    low_stock = Product.objects.filter(stock__gt=0, stock__lte=5).count()

    return {
        "orders_total": orders_total,
        "orders_pending": orders_pending,
        "orders_paid": orders_paid,
        "orders_failed": orders_failed,
        "units_sold": units_sold,
        "revenue": revenue,
        "products_total": products_total,
        "products_in_stock": products_in_stock,
        "products_out": products_out,
        "low_stock": low_stock,
        "url_orders": reverse("admin:orders_order_changelist"),
        "url_order_items": reverse("admin:orders_orderitem_changelist"),
        "url_products": reverse("admin:products_product_changelist"),
        "url_carts": reverse("admin:products_cart_changelist"),
    }
