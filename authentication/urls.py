from django.urls import path
from . import views
from products import views as product_views
from products import cart_views
from products import search_views
from posts import views as post_views
from users import views as user_views

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
    
    # Categories
    path('v1/categories/', product_views.categories_api, name='categories_api'),
    
    # Cart
    path('v1/cart/', cart_views.view_cart_api, name='view_cart_api'),
    path('v1/cart/add/', cart_views.add_to_cart_api, name='add_to_cart_api'),
    path('v1/cart/item/<int:item_id>/', cart_views.update_cart_item_api, name='update_cart_item_api'),
    path('v1/cart/item/<int:item_id>/remove/', cart_views.remove_from_cart_api, name='remove_from_cart_api'),
    path('v1/cart/clear/', cart_views.clear_cart_api, name='clear_cart_api'),
    
    # Posts/Products
    path('v1/posts/', product_views.create_product_api, name='create_product_api'),
    path('v1/posts/<int:post_id>/', post_views.post_detail_api, name='post_detail_api'),
    path('v1/posts/<int:post_id>/edit/', product_views.edit_product_api, name='edit_product_api'),
    path('v1/posts/<int:post_id>/delete/', product_views.delete_product_api, name='delete_product_api'),
    path('v1/posts/<int:post_id>/purchase/', product_views.purchase_product_api, name='purchase_product_api'),
    path('v1/my-products/', product_views.my_products_api, name='my_products_api'),
    
    # Bookmarks & Likes
    path('v1/bookmark/<int:post_id>/', post_views.bookmark_toggle_api, name='bookmark_toggle_api'),
    path('v1/bookmarks/', post_views.bookmarks_api, name='bookmarks_api'),
    path('v1/like/<int:post_id>/', post_views.like_post_api, name='like_post_api'),
    
    # Purchases
    path('v1/purchases/bulk/', product_views.bulk_purchase_api, name='bulk_purchase_api'),
    
    # Search
    path('v1/search/', search_views.search_products_api, name='search_products_api'),
    path('v1/search/suggestions/', search_views.search_suggestions_api, name='search_suggestions_api'),
    
    # User Settings & Profile
    path('v1/settings/', user_views.user_settings_api, name='user_settings_api'),
    path('v1/become-vendor/', user_views.become_vendor_api, name='become_vendor_api'),
    path('v1/vendor-dashboard/', user_views.vendor_dashboard_api, name='vendor_dashboard_api'),
    path('v1/purchases/', user_views.purchase_history_api, name='purchase_history_api'),
]

# Add api_endpoints to main urlpatterns
urlpatterns += api_endpoints
