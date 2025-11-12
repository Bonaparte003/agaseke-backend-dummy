from django.db import models
from users.models import User
import uuid

class Purchase(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('awaiting_pickup', 'Awaiting Pickup'),
        ('awaiting_delivery', 'Awaiting Delivery'),
        ('out_for_delivery', 'Out for Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    DELIVERY_CHOICES = (
        ('pickup', 'Pickup from agaseke'),
        ('delivery', 'Home Delivery'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('momo', 'Mobile Money'),
        ('credit', 'Credit Card'),
    )
    
    order_id = models.CharField(max_length=50, unique=True, blank=True)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey('posts.Post', on_delete=models.CASCADE, related_name='purchases')
    quantity = models.IntegerField(default=1)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='pickup')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='momo')
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    delivery_address = models.TextField(blank=True, null=True, help_text="Delivery address for home delivery")
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # agaseke workflow fields
    agaseke_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='agaseke_purchases', 
                                     help_text="agaseke user handling this purchase")
    pickup_confirmed_at = models.DateTimeField(null=True, blank=True)
    vendor_payment_sent = models.BooleanField(default=False)
    agaseke_commission_sent = models.BooleanField(default=False)
    vendor_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    agaseke_commission_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            # Generate a unique order ID
            self.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Set delivery fee if delivery method is delivery
        if self.delivery_method == 'delivery' and self.delivery_fee == 0:
            from decimal import Decimal
            self.delivery_fee = Decimal('5.00')  # RWF5 delivery fee
        
        # Calculate payment splits when status changes to completed
        if self.status == 'completed' and not self.vendor_payment_amount:
            from decimal import Decimal
            total_amount = self.purchase_price + self.delivery_fee
            product_amount = self.purchase_price
            self.vendor_payment_amount = product_amount * Decimal('0.8')  # 80% of product price to vendor
            self.agaseke_commission_amount = (product_amount * Decimal('0.2')) + self.delivery_fee  # 20% of product + full delivery fee to agaseke
        
        super().save(*args, **kwargs)
    
    def calculate_payment_split(self):
        """Calculate the 80/20 payment split including delivery fees"""
        from decimal import Decimal
        product_amount = self.purchase_price
        total_amount = product_amount + self.delivery_fee
        return {
            'total': total_amount,
            'product_amount': product_amount,
            'delivery_fee': self.delivery_fee,
            'vendor_amount': product_amount * Decimal('0.8'),
            'agaseke_amount': (product_amount * Decimal('0.2')) + self.delivery_fee
        }
    
    def __str__(self):
        return f"{self.buyer.username} - {self.product.title} - {self.order_id}"
    
    class Meta:
        ordering = ['-created_at']

class ProductImage(models.Model):
    product = models.ForeignKey('posts.Post', on_delete=models.CASCADE, related_name='auxiliary_images')
    image = models.ImageField(upload_to='product_gallery/')
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.title} - Image {self.display_order + 1}"
    
    class Meta:
        ordering = ['display_order']


class Cart(models.Model):
    """Shopping cart for a user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.username}"
    
    def total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())
    
    def total_price(self):
        """Calculate total price of all items in cart"""
        from decimal import Decimal
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.subtotal()
        return total
    
    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()


class CartItem(models.Model):
    """Individual item in a shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('posts.Post', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['cart', 'product']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.title} in {self.cart.user.username}'s cart"
    
    def subtotal(self):
        """Calculate subtotal for this cart item"""
        from decimal import Decimal
        return Decimal(str(self.product.price)) * Decimal(str(self.quantity))
    
    def is_available(self):
        """Check if product has enough inventory"""
        return self.product.inventory >= self.quantity