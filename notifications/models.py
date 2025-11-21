from django.db import models
from users.models import User
from django.utils import timezone


class NotificationPreferences(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # General notification toggle
    notifications_enabled = models.BooleanField(default=True, help_text="Master toggle for all notifications")
    
    # Specific notification types for buyers
    purchase_created_enabled = models.BooleanField(default=True, help_text="Notify when purchase is confirmed")
    purchase_status_changed_enabled = models.BooleanField(default=True, help_text="Notify when purchase status changes")
    purchase_completed_enabled = models.BooleanField(default=True, help_text="Notify when purchase is completed")
    
    # Specific notification types for vendors
    product_purchased_enabled = models.BooleanField(default=True, help_text="Notify vendor when product is purchased")
    product_purchase_completed_enabled = models.BooleanField(default=True, help_text="Notify vendor when purchase is completed")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.username}"
    
    class Meta:
        verbose_name_plural = "Notification preferences"


class Notification(models.Model):
    """Store notification history"""
    NOTIFICATION_TYPES = (
        ('purchase_created', 'Purchase Created'),
        ('purchase_pending', 'Purchase Pending'),
        ('purchase_processing', 'Purchase Processing'),
        ('purchase_awaiting_pickup', 'Purchase Awaiting Pickup'),
        ('purchase_awaiting_delivery', 'Purchase Awaiting Delivery'),
        ('purchase_out_for_delivery', 'Purchase Out for Delivery'),
        ('purchase_completed', 'Purchase Completed'),
        ('purchase_cancelled', 'Purchase Cancelled'),
        ('product_purchased', 'Product Purchased (Vendor)'),
        ('product_purchase_completed', 'Product Purchase Completed (Vendor)'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    body = models.TextField()
    
    # Optional reference to the purchase
    purchase = models.ForeignKey('products.Purchase', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    # Seen status
    seen = models.BooleanField(default=False, help_text="User has seen notification")
    seen_at = models.DateTimeField(null=True, blank=True, help_text="When notification was seen")
    
    # Additional data (JSON format for flexibility)
    data = models.JSONField(default=dict, blank=True, help_text="Additional notification data")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'seen']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.title}"
    
    def mark_as_seen(self):
        """Mark notification as seen"""
        if not self.seen:
            self.seen = True
            self.seen_at = timezone.now()
            self.save(update_fields=['seen', 'seen_at'])
