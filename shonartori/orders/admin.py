from django.contrib import admin
from django.db.models import F, IntegerField, Sum
from django.db.models.expressions import ExpressionWrapper
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "quantity", "unit_price_display", "line_total_display", "status"]
    can_delete = False
    verbose_name_plural = "Order lines"

    @admin.display(description="Unit (৳)")
    def unit_price_display(self, obj):
        if obj.pk and obj.price is not None:
            return f"৳{obj.price:,}"
        return "—"

    @admin.display(description="Line (৳)")
    def line_total_display(self, obj):
        if obj.pk and obj.price is not None:
            return f"৳{obj.get_total_price():,}"
        return "—"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_list_template = "admin/orders/order/change_list.html"

    list_display = [
        "short_uid",
        "customer_display",
        "line_count",
        "total_display",
        "status_display",
        "inventory_badge",
        "created_at",
    ]
    list_display_links = ["short_uid"]
    list_filter = ["status", "inventory_committed", "payment_method"]
    search_fields = [
        "uid",
        "user__email",
        "user__username",
        "user__first_name",
        "user__last_name",
        "transaction_id",
        "phone",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 50
    show_full_result_count = True
    list_select_related = ["user"]
    readonly_fields = [
        "uid",
        "user",
        "total_price",
        "inventory_committed",
        "created_at",
        "updated_at",
    ]
    inlines = [OrderItemInline]

    fieldsets = (
        (
            "Order summary",
            {
                "fields": ("uid", "user", "status", "total_price", "inventory_committed"),
                "description": "Inventory committed means stock was deducted for this order.",
            },
        ),
        (
            "Customer & delivery",
            {"fields": ("address", "phone")},
        ),
        (
            "Payment",
            {
                "fields": ("transaction_id", "payment_method"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Order #", ordering="uid")
    def short_uid(self, obj):
        s = str(obj.uid)
        return s[:8] + "…"

    @admin.display(description="Customer")
    def customer_display(self, obj):
        u = obj.user
        name = (u.get_full_name() or "").strip() or u.username
        return format_html(
            '<strong>{}</strong><br><span class="mini quiet">{}</span>',
            name,
            u.email,
        )

    @admin.display(description="Lines")
    def line_count(self, obj):
        return obj.order_items.count()

    @admin.display(description="Total (৳)", ordering="total_price")
    def total_display(self, obj):
        return f"৳{obj.total_price:,}"

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        css = {
            "paid": "st-pill st-pill--paid",
            "pending": "st-pill st-pill--pending",
            "failed": "st-pill st-pill--failed",
            "cancelled": "st-pill st-pill--cancelled",
            "shipped": "st-pill st-pill--shipped",
            "delivered": "st-pill st-pill--delivered",
        }.get(obj.status, "st-pill st-pill--default")
        label = obj.get_status_display()
        return format_html('<span class="{}">{}</span>', css, label)

    @admin.display(description="Stock", boolean=True)
    def inventory_badge(self, obj):
        return obj.inventory_committed

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
        extra_context["orders_pending_count"] = Order.objects.filter(status="pending").count()
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "order_link",
        "product",
        "quantity",
        "unit_price_display",
        "line_total_display",
        "status_display",
        "order_created",
    ]
    list_filter = ["status", "order__status"]
    search_fields = ["product__product_name", "order__uid", "order__user__email"]
    ordering = ["-order__created_at"]
    list_per_page = 100
    show_full_result_count = True
    list_select_related = ["order", "order__user", "product"]
    readonly_fields = [
        "order",
        "product",
        "quantity",
        "price",
        "status",
        "line_total_display",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": ("order", "product", "quantity", "price", "line_total_display", "status"),
            },
        ),
    )

    @admin.display(description="Unit (৳)")
    def unit_price_display(self, obj):
        if obj.price is not None:
            return f"৳{obj.price:,}"
        return "—"

    @admin.display(description="Line (৳)")
    def line_total_display(self, obj):
        if obj.price is not None:
            return f"৳{obj.get_total_price():,}"
        return "—"

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        return obj.get_status_display()

    @admin.display(description="Order", ordering="order__created_at")
    def order_link(self, obj):
        from django.urls import reverse

        url = reverse("admin:orders_order_change", args=[obj.order.pk])
        short = str(obj.order.uid)[:8]
        return format_html('<a href="{}">{}…</a>', url, short)

    @admin.display(description="Placed", ordering="order__created_at")
    def order_created(self, obj):
        return obj.order.created_at

    def has_add_permission(self, request):
        return False
