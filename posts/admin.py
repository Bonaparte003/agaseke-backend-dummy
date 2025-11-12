from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Post, ProductReview, Bookmark

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for managing product categories"""
    list_display = ('name', 'slug', 'category_image_preview', 'product_count_display', 'is_active', 'display_order', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')  # Enable search for autocomplete
    prepopulated_fields = {'slug': ('name',)}  # Auto-generate slug from name
    list_editable = ('is_active', 'display_order')  # Quick edit in list view
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Visual', {
            'fields': ('category_image',),
            'description': 'Upload an image to visually represent this category'
        }),
        ('Settings', {
            'fields': ('is_active', 'display_order'),
            'description': 'Control category visibility and display order'
        }),
    )
    
    def category_image_preview(self, obj):
        """Show thumbnail of category image in list view"""
        if obj.category_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />',
                obj.category_image.url
            )
        return format_html('<span style="color: #999;">No image</span>')
    category_image_preview.short_description = 'Image'
    
    def product_count_display(self, obj):
        """Show count of products in this category"""
        count = obj.product_count()
        if count > 0:
            return format_html('<strong>{}</strong> products', count)
        return format_html('<span style="color: #999;">0 products</span>')
    product_count_display.short_description = 'Products'

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'price', 'category', 'inventory', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')
    autocomplete_fields = ['category']  # Searchable dropdown for category

class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__username', 'product__title')

# Register your models here.
admin.site.register(Post, PostAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(Bookmark)