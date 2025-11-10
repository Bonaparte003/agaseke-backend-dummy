from django.contrib import admin
from .models import UserQRCode, OTPVerification

# Register authentication app models only
admin.site.register(UserQRCode)
admin.site.register(OTPVerification)
