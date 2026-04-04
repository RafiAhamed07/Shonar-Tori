from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, ColorVariant, SizeVariant, Cart, CartItem


class ProductImageInline(admin.StackedInline):
    model = ProductImage
    extra = 0
    verbose_name_plural = "Product images"


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


class LowStockFilter(admin.SimpleListFilter):
    title = "stock alert"
    parameter_name = "stock_alert"

    def lookups(self, request, model_admin):
        return (("low", "Low stock (1–5 units)"),)

    def queryset(self, request, queryset):
        if self.value() == "low":
            return queryset.filter(stock__gte=1, stock__lte=5)
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "product_name",
        "category",
        "price_display",
        "stock",
        "stock_badge",
        "updated_at",
    ]
    list_display_links = ["product_name"]
    list_filter = ["category", InStockFilter, LowStockFilter]
    search_fields = ["product_name", "slug", "product_description"]
    list_editable = ["stock"]
    ordering = ["-updated_at"]
    list_per_page = 25
    show_full_result_count = True
    date_hierarchy = None
    autocomplete_fields = ["category"]
    filter_horizontal = ("color_variant", "size_variant")
    readonly_fields = ["uid", "slug", "created_at", "updated_at"]
    inlines = [ProductImageInline]

    fieldsets = (
        (
            "Product",
            {
                "fields": ("product_name", "slug", "category", "product_description"),
                "description": "Slug is generated from the name when saved.",
            },
        ),
        (
            "Pricing & inventory",
            {
                "fields": ("price", "stock"),
                "description": "Stock = 0 shows as out of stock on the storefront.",
            },
        ),
        (
            "Variants",
            {
                "fields": ("color_variant", "size_variant"),
                "classes": ("collapse",),
            },
        ),
        (
            "System",
            {
                "fields": ("uid", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Price (৳)", ordering="price")
    def price_display(self, obj):
        return f"৳{obj.price:,}"

    @admin.display(description="Stock status")
    def stock_badge(self, obj):
        if obj.stock > 0:
            return format_html(
                '<span class="st-stock-ok">In stock — {} units</span>',
                obj.stock,
            )
        return format_html('<span class="st-stock-no">Out of stock</span>')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["category_name", "slug", "updated_at"]
    search_fields = ["category_name", "slug"]
    ordering = ["category_name"]
    readonly_fields = ["uid", "slug", "created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("category_name", "category_image")}),
        (
            "System",
            {"fields": ("uid", "slug", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "thumbnail_preview", "updated_at"]
    list_filter = ["product__category"]
    search_fields = ["product__product_name"]
    autocomplete_fields = ["product"]
    readonly_fields = ["uid", "created_at", "updated_at", "image_preview"]

    fieldsets = (
        (None, {"fields": ("product", "image", "image_preview")}),
        (
            "System",
            {"fields": ("uid", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Preview")
    def thumbnail_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" width="48" height="48" style="object-fit:cover;border-radius:4px;" />',
                obj.image.url,
            )
        return "—"

    @admin.display(description="Large preview")
    def image_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-height:200px;border-radius:4px;" />',
                obj.image.url,
            )
        return "—"


@admin.register(ColorVariant)
class ColorVariantAdmin(admin.ModelAdmin):
    list_display = ["color_name", "price", "updated_at"]
    search_fields = ["color_name"]
    ordering = ["color_name"]
    readonly_fields = ["uid", "created_at", "updated_at"]


@admin.register(SizeVariant)
class SizeVariantAdmin(admin.ModelAdmin):
    list_display = ["size_name", "price", "updated_at"]
    search_fields = ["size_name"]
    ordering = ["size_name"]
    readonly_fields = ["uid", "created_at", "updated_at"]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["product", "quantity", "line_total_display"]
    can_delete = False
    verbose_name_plural = "Cart lines"

    @admin.display(description="Line total (৳)")
    def line_total_display(self, obj):
        if obj.pk:
            return f"৳{obj.get_total_price():,}"
        return "—"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["short_uid", "user", "item_count", "cart_subtotal_display", "updated_at"]
    search_fields = ["user__email", "user__username", "uid"]
    ordering = ["-updated_at"]
    list_filter = ["created_at"]
    date_hierarchy = "created_at"
    inlines = [CartItemInline]
    readonly_fields = ["uid", "user", "created_at", "updated_at"]
    list_select_related = ["user"]

    @admin.display(description="Cart ID")
    def short_uid(self, obj):
        return str(obj.uid)[:8] + "…"

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.cart_items.count()

    @admin.display(description="Subtotal (৳)")
    def cart_subtotal_display(self, obj):
        total = sum(i.get_total_price() for i in obj.cart_items.all())
        return f"৳{total:,}"
