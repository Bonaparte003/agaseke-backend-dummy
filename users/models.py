from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_ROLES = (
        ('user', 'User'),
        ('staff', 'Staff'), 
        ('vendor', 'Vendor'),
        ('agaseke', 'agaseke'),
    )
    
    # Base role for all users
    role = models.CharField(max_length=20, choices=USER_ROLES, default='user')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Additional role flags to support multiple roles
    is_vendor_role = models.BooleanField(default=False)
    
    # Profile picture
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Stats
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_purchases = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def is_user(self):
        return self.role == 'user' and not self.is_vendor_role
    
    def is_staff_member(self):
        return self.role == 'staff'
    
    def is_vendor(self):
        return self.is_vendor_role
    
    def is_agaseke(self):
        return self.role == 'agaseke'

