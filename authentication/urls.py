from django.urls import path
from . import views

urlpatterns = [
    # API endpoints for QR code scanning and verification flow
    path('api/purchases/by-qr/', views.get_purchases_by_qr, name='api_get_purchases_by_qr'),
    path('api/verify-credentials/', views.verify_buyer_credentials, name='api_verify_credentials'),
    path('api/send-otp/', views.send_otp, name='api_send_otp'),
    path('api/verify-otp/', views.verify_otp_view, name='api_verify_otp'),
    path('api/complete-purchase/', views.complete_purchase_pickup, name='api_complete_purchase'),
    path('api/complete-purchases-bulk/', views.complete_purchases_bulk, name='api_complete_purchases_bulk'),
    path('api/vendors/', views.get_all_vendors_api, name='api_get_all_vendors'),
    path('api/vendors/<int:vendor_id>/', views.get_vendor_profile_api, name='api_get_vendor_profile'),
    path('api/vendor-statistics/<int:vendor_id>/', views.get_vendor_statistics_modal, name='api_vendor_statistics_modal'),
]

# API endpoints (v1 - JSON APIs)
api_endpoints = [
    # Authentication
    path('v1/register/', views.register_api, name='register_api'),
    path('v1/login/', views.login_api, name='login_api'),
    path('v1/login/verify-otp/', views.verify_login_otp_api, name='verify_login_otp_api'),
    path('v1/logout/', views.logout_api, name='logout_api'),
    path('v1/token/refresh/', views.refresh_token_api, name='refresh_token_api'),
    
    # Dashboard
    path('v1/dashboard/', views.dashboard_api, name='dashboard_api'),
    
    # QR Code
    path('v1/qr-code/', views.user_qr_code_api, name='user_qr_code_api'),  # GET/POST - Get QR code in base64
    
    # Agaseke Dashboard
    path('v1/agaseke-dashboard/', views.agaseke_dashboard_api, name='agaseke_dashboard_api'),
]

# Add api_endpoints to main urlpatterns
urlpatterns += api_endpoints
