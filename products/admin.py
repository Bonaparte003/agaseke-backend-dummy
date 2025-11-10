from django.contrib import admin
from .models import Purchase, ProductImage

class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'product', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'delivery_method', 'created_at')
    search_fields = ('buyer__username', 'product__title')

# Register your models here.
admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(ProductImage)