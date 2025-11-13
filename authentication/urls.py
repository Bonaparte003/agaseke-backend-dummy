from django.urls import path, include
from . import views  # authentication views (QR, agaseke specific)
from . import api_views
from django.contrib.auth import views as auth_views
from users import views as users_views
from posts import views as posts_views
from products import views as products_views
from products import cart_views
from products import search_views

urlpatterns = [
    path('register/', views.register, name='register'),  # Still in authentication
    path('login/', views.login_view, name='login'),  # Still in authentication
    path('logout/', views.logout_view, name='logout'),  # Still in authentication
    path('dashboard/', views.dashboard, name='dashboard'),  # Keep in authentication for now
    path('settings/', users_views.user_settings, name='user_settings'),
    
    # Post creation and interaction (HTML views - legacy)
    path('create-post/', posts_views.create_post, name='create_post'),
    path('create-product/', products_views.create_product, name='create_product'),
    path('edit-product/<int:product_id>/', products_views.edit_product, name='edit_product'),
    path('like-post/<int:post_id>/', posts_views.like_post, name='like_post'),
    
    # Post detail and actions (HTML views - legacy)
    path('post/<int:post_id>/', posts_views.post_detail, name='post_detail'),
    path('post/<int:post_id>/purchase/', products_views.purchase_product, name='purchase_product'),
    path('bookmark/<int:post_id>/', posts_views.bookmark_toggle, name='bookmark_toggle'),
    
    # User dashboards (HTML views - legacy)
    path('vendor-dashboard/', users_views.vendor_dashboard, name='vendor_dashboard'),
    
    # User history and saved items (HTML views - legacy)
    path('purchases/', users_views.purchase_history, name='purchase_history'),
    path('bookmarks/', posts_views.bookmarks, name='bookmarks'),
    
    # Legacy paths (kept for compatibility)
    path('become-vendor/', users_views.become_vendor, name='become_vendor'),
    
    # agaseke specific URLs
    path('qr-code/', views.user_qr_code, name='user_qr_code'),
    path('agaseke-dashboard/', views.agaseke_dashboard, name='agaseke_dashboard'),
    path('scan-qr/', views.scan_qr_code, name='scan_qr_code'),
    path('confirm-pickup/<int:purchase_id>/', views.confirm_purchase_pickup, name='confirm_purchase_pickup'),
    path('confirm-delivery/<int:purchase_id>/', views.confirm_delivery, name='confirm_delivery'),
    path('update-qr-ajax/', views.update_qr_code_ajax, name='update_qr_code_ajax'),
    path('agaseke-history/', users_views.agaseke_purchase_history, name='agaseke_purchase_history'),
    path('sales-statistics/', users_views.sales_statistics, name='sales_statistics'),
    path('vendor-statistics/<int:vendor_id>/', users_views.vendor_statistics_for_agaseke, name='vendor_statistics_for_agaseke'),
    
    # API endpoints for QR code scanning and verification flow
    path('api/purchases/by-qr/', api_views.get_purchases_by_qr, name='api_get_purchases_by_qr'),
    path('api/verify-credentials/', api_views.verify_buyer_credentials, name='api_verify_credentials'),
    path('api/send-otp/', api_views.send_otp, name='api_send_otp'),
    path('api/verify-otp/', api_views.verify_otp_view, name='api_verify_otp'),
    path('api/complete-purchase/', api_views.complete_purchase_pickup, name='api_complete_purchase'),
    path('api/vendor-statistics/<int:vendor_id>/', api_views.get_vendor_statistics_modal, name='api_vendor_statistics_modal'),
]

# API endpoints (v1 - JSON APIs)
api_endpoints = [
    # Authentication
    path('v1/register/', views.register_api, name='register_api'),
    path('v1/login/', views.login_api, name='login_api'),
    path('v1/login/verify-otp/', views.verify_login_otp_api, name='verify_login_otp_api'),
    path('v1/logout/', views.logout_api, name='logout_api'),
    path('v1/token/refresh/', views.refresh_token_api, name='refresh_token_api'),
    
    # Dashboard & Products
    path('v1/dashboard/', views.dashboard_api, name='dashboard_api'),
    path('v1/posts/<int:post_id>/', posts_views.post_detail_api, name='post_detail_api'),  # GET - View post
    path('v1/posts/', products_views.create_product_api, name='create_product_api'),  # POST - Create product
    path('v1/posts/<int:post_id>/edit/', products_views.edit_product_api, name='edit_product_api'),  # PUT/PATCH - Edit product
    path('v1/posts/<int:post_id>/delete/', products_views.delete_product_api, name='delete_product_api'),  # DELETE - Delete product
    path('v1/posts/<int:post_id>/purchase/', products_views.purchase_product_api, name='purchase_product_api'),  # POST - Single purchase (legacy)
    path('v1/purchases/bulk/', products_views.bulk_purchase_api, name='bulk_purchase_api'),  # POST - Bulk purchase
    
    # User interactions
    path('v1/bookmark/<int:post_id>/', posts_views.bookmark_toggle_api, name='bookmark_toggle_api'),
    path('v1/bookmarks/', posts_views.bookmarks_api, name='bookmarks_api'),
    path('v1/like/<int:post_id>/', posts_views.like_post_api, name='like_post_api'),
    
    # User data
    path('v1/purchases/', users_views.purchase_history_api, name='purchase_history_api'),
    path('v1/settings/', users_views.user_settings_api, name='user_settings_api'),
    path('v1/qr-code/', views.user_qr_code_api, name='user_qr_code_api'),  # GET/POST - Get QR code in base64
    path('v1/become-vendor/', users_views.become_vendor_api, name='become_vendor_api'),
    path('v1/vendor-dashboard/', users_views.vendor_dashboard_api, name='vendor_dashboard_api'),
    path('v1/agaseke-dashboard/', views.agaseke_dashboard_api, name='agaseke_dashboard_api'),
    
    # Categories
    path('v1/categories/', products_views.categories_api, name='categories_api'),
    
    # Shopping Cart
    path('v1/cart/', cart_views.view_cart_api, name='view_cart_api'),  # GET - View cart
    path('v1/cart/add/', cart_views.add_to_cart_api, name='add_to_cart_api'),  # POST - Add to cart
    path('v1/cart/item/<int:item_id>/', cart_views.update_cart_item_api, name='update_cart_item_api'),  # PUT/PATCH - Update quantity
    path('v1/cart/item/<int:item_id>/remove/', cart_views.remove_from_cart_api, name='remove_from_cart_api'),  # DELETE - Remove item
    path('v1/cart/clear/', cart_views.clear_cart_api, name='clear_cart_api'),  # POST/DELETE - Clear cart
    
    # Search
    path('v1/search/', search_views.search_products_api, name='search_products_api'),  # GET - Advanced search
    path('v1/search/suggestions/', search_views.search_suggestions_api, name='search_suggestions_api'),  # GET - Autocomplete
]

# Add api_endpoints to main urlpatterns
urlpatterns += api_endpoints