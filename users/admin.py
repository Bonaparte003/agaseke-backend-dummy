from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    # Add the custom fields to the admin interface
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'role', 'is_vendor_role', 'profile_picture', 'total_sales', 'total_purchases')
        }),
    )
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_vendor_role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_vendor_role', 'is_staff', 'is_active')

# Register your models here.
admin.site.register(User, UserAdmin)