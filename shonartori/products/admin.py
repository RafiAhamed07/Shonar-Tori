from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, ColorVariant, SizeVariant, Cart, CartItem


class ProductImageInline(admin.StackedInline):
    model = ProductImage
    extra = 1


class InStockFilter(admin.SimpleListFilter):
    title = "availability"
    parameter_name = "in_stock"

    def lookups(self, request, model_admin):
        return (
            ("yes", "In stock"),
            ("no", "Out of stock"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(stock__gt=0)
        if self.value() == "no":
            return queryset.filter(stock=0)
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "product_name",
        "category",
        "price",
        "stock",
        "stock_badge",
    ]
    list_filter = ["category", InStockFilter]
    search_fields = ["product_name", "slug"]
    list_editable = ["stock"]
    inlines = [ProductImageInline]

    @admin.display(description="Stock status")
    def stock_badge(self, obj):
        if obj.stock > 0:
            return format_html(
                '<span style="color:green;font-weight:bold;">In stock ({})</span>',
                obj.stock,
            )
        return format_html('<span style="color:#c00;font-weight:bold;">Out of stock</span>')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["product", "quantity", "line_total_display"]
    can_delete = False

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        if obj.pk:
            return obj.get_total_price()
        return "—"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["uid", "user", "item_count", "created_at"]
    search_fields = ["user__email", "user__username"]
    inlines = [CartItemInline]
    readonly_fields = ["uid", "created_at", "updated_at"]

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.cart_items.count()


admin.site.register(Category)
admin.site.register(ProductImage)
admin.site.register(ColorVariant)
admin.site.register(SizeVariant)
