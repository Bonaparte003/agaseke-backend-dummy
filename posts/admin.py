from django.contrib import admin
from .models import Post, ProductReview, Bookmark

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'price', 'category', 'inventory', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')

class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__username', 'product__title')

# Register your models here.
admin.site.register(Post, PostAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(Bookmark)