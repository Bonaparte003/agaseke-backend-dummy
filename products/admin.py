from django.contrib import admin
from django.utils.html import format_html
from .models import Purchase, ProductImage, Cart, CartItem

class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'product', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'delivery_method', 'created_at')
    search_fields = ('buyer__username', 'product__title')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'quantity', 'subtotal_display', 'is_available')
    readonly_fields = ('subtotal_display', 'is_available')
    
    def subtotal_display(self, obj):
        return format_html('<strong>${}</strong>', obj.subtotal())
    subtotal_display.short_description = 'Subtotal'
    
    def is_available(self, obj):
        if obj.is_available():
            return format_html('<span style="color: green;">✓ Available</span>')
        else:
            return format_html('<span style="color: red;">✗ Out of Stock</span>')
    is_available.short_description = 'Availability'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items_display', 'total_price_display', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'total_items_display', 'total_price_display')
    inlines = [CartItemInline]
    
    def total_items_display(self, obj):
        count = obj.total_items()
        if count > 0:
            return format_html('<strong>{}</strong> items', count)
        return '0 items'
    total_items_display.short_description = 'Total Items'
    
    def total_price_display(self, obj):
        total = obj.total_price()
        return format_html('<strong>${:.2f}</strong>', total)
    total_price_display.short_description = 'Total Price'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart_user', 'product', 'quantity', 'subtotal_display', 'is_available_display', 'added_at')
    list_filter = ('added_at', 'updated_at')
    search_fields = ('cart__user__username', 'product__title')
    readonly_fields = ('added_at', 'updated_at', 'subtotal_display')
    
    def cart_user(self, obj):
        return obj.cart.user.username
    cart_user.short_description = 'User'
    
    def subtotal_display(self, obj):
        return format_html('<strong>${:.2f}</strong>', obj.subtotal())
    subtotal_display.short_description = 'Subtotal'
    
    def is_available_display(self, obj):
        if obj.is_available():
            return format_html('<span style="color: green;">✓ In Stock</span>')
        else:
            return format_html('<span style="color: red;">✗ Insufficient Stock</span>')
    is_available_display.short_description = 'Stock Status'


# Register your models here.
admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(ProductImage)