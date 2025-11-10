from django.db import models
from users.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Post(models.Model):
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
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
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