from django.db import models
from users.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify

class Category(models.Model):
    """Product category with image support"""
    name = models.CharField(max_length=100, unique=True, help_text="Category name (e.g., Electronics)")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly version (auto-generated)")
    description = models.TextField(blank=True, help_text="Optional category description")
    category_image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True,
        help_text="Category icon/image for visual representation"
    )
    is_active = models.BooleanField(default=True, help_text="Show/hide category")
    display_order = models.IntegerField(default=0, help_text="Order in which categories are displayed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def product_count(self):
        """Return count of active products in this category"""
        return self.posts.filter(inventory__gt=0).count()

class Post(models.Model):
    # Keep old CATEGORY_CHOICES for backward compatibility during migration
    CATEGORY_CHOICES = (
        ('electronics', 'Electronics'),
        ('books_media', 'Books & Media'),
        ('home_kitchen', 'Home & Kitchen'),
        ('beauty_care', 'Beauty & Personal Care'),
        ('software_services', 'Software & Services'),
        ('health_fitness', 'Health & Fitness'),
        ('other', 'Other'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='posts/')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    
    # Product fields
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # NEW: Use ForeignKey to Category model
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        help_text="Product category"
    )
    # Temporary field for migration - will be removed after migration 0005
    # old_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other', blank=True)
    inventory = models.IntegerField(default=1, help_text="Number of items in stock")
    
    # Stats
    total_purchases = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title
        
    def total_likes(self):
        return self.likes.count()
    
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0
    
    def review_count(self):
        return self.reviews.count()
    
    def is_sold_out(self):
        return self.inventory <= 0
    
    class Meta:
        ordering = ['-created_at']

class ProductReview(models.Model):
    product = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'reviewer']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.reviewer.username} - {self.product.title} - {self.rating} stars"

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.post.title}"
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'post']