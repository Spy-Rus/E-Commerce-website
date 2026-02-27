from django.contrib import admin
from .models import Product, ProductImage, Order, OrderItem

# =========================
# Product Image Inline
# =========================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


# =========================
# Product Admin
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'current_price',
        'inventory',
        'available',
        'created',
        'last_update',
    )

    list_filter = (
        'available',
        'created',
        'last_update',
    )

    search_fields = (
        'title',
        'description',
    )

    prepopulated_fields = {
        'slug': ('title',)
    }

    readonly_fields = (
        'created',
        'last_update',
    )

    inlines = [
        ProductImageInline
    ]

    def current_price(self, obj):
        return obj.get_current_price()

    current_price.short_description = "Current Price"


# =========================
# Order Item Inline
# =========================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_purchase')


# =========================
# Order Admin (ONLY ONE)
# =========================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'status',
        'total_price',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'id',
        'user__username',
        'user__email',
    )

    ordering = ('-created_at',)

    readonly_fields = (
        'user',
        'total_price',
        'created_at',
    )

    inlines = [
        OrderItemInline
    ]


# =========================
# Optional ProductImage Admin
# =========================
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'image',
    )
