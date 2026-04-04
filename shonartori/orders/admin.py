from django.contrib import admin
from django.db.models import F, IntegerField, Sum
from django.db.models.expressions import ExpressionWrapper

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "quantity", "price", "line_total_display", "status"]
    can_delete = False

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        if obj.pk:
            return obj.get_total_price()
        return "—"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_list_template = "admin/orders/order/change_list.html"

    list_display = [
        "uid",
        "user",
        "total_price",
        "status",
        "inventory_committed",
        "created_at",
    ]
    list_filter = ["status", "inventory_committed"]
    search_fields = ["uid", "user__email", "user__username", "transaction_id"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    readonly_fields = ["uid", "created_at", "updated_at"]
    inlines = [OrderItemInline]

    fieldsets = (
        (None, {"fields": ("uid", "user", "status", "total_price", "inventory_committed")}),
        ("Shipping / payment", {"fields": ("address", "phone", "transaction_id", "payment_method")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        paid_lines = OrderItem.objects.filter(order__status="paid")
        extra_context["sales_units_paid"] = paid_lines.aggregate(t=Sum("quantity"))["t"] or 0
        line_total = ExpressionWrapper(
            F("price") * F("quantity"),
            output_field=IntegerField(),
        )
        extra_context["sales_revenue_paid"] = (
            paid_lines.aggregate(t=Sum(line_total))["t"] or 0
        )
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "product",
        "quantity",
        "price",
        "line_total_display",
        "status",
        "order_created",
    ]
    list_filter = ["status", "order__status"]
    search_fields = ["product__product_name", "order__uid"]
    ordering = ["-order__created_at"]
    readonly_fields = ["order", "product", "quantity", "price", "status", "line_total_display"]

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        return obj.get_total_price()

    @admin.display(description="Order date", ordering="order__created_at")
    def order_created(self, obj):
        return obj.order.created_at

    def has_add_permission(self, request):
        return False
