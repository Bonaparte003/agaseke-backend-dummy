import os
import csv
import io
import json
from datetime import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect, csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from users.models import User
from posts.models import Post, ProductReview, Bookmark
from products.models import Purchase, ProductImage
from .models import UserQRCode, OTPVerification
from .qr_utils import update_user_qr_code, decode_qr_data, get_user_purchases_from_qr
from .otp_utils import create_otp, verify_otp as verify_otp_util
from .jwt_utils import get_tokens_for_user, get_user_from_token, refresh_access_token


def get_token_user(request):
    """Helper function to get user from token authentication (JWT or legacy token)"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.replace('Bearer ', '')
    
    # Try JWT token first
    user = get_user_from_token(token)
    if user:
        return user
    
    # Fallback to legacy token authentication (for backward compatibility)
    try:
        from rest_framework.authtoken.models import Token
        token_obj = Token.objects.get(key=token)
        return token_obj.user
    except:
        return None


@csrf_exempt
@require_http_methods(["POST"])
def register_api(request):
    """API endpoint for user registration - accepts single password field"""
    try:
        # Check content type
        content_type = request.content_type
        
        # Handle both JSON and form data
        if content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data',
                    'errors': {'json': ['Request body contains invalid JSON']}
                }, status=400)
        else:
            # Handle form data
            data = request.POST.dict()
        
        # Extract required fields
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone_number = data.get('phone_number', '').strip()
        password = data.get('password', '')
        
        # Validate required fields
        errors = {}
        
        if not username:
            errors['username'] = ['This field is required']
        elif User.objects.filter(username=username).exists():
            errors['username'] = ['A user with that username already exists']
        elif len(username) < 3:
            errors['username'] = ['Username must be at least 3 characters long']
        
        if not email:
            errors['email'] = ['This field is required']
        elif User.objects.filter(email=email).exists():
            errors['email'] = ['A user with that email already exists']
        elif '@' not in email:
            errors['email'] = ['Enter a valid email address']
        
        if not first_name:
            errors['first_name'] = ['This field is required']
        
        if not last_name:
            errors['last_name'] = ['This field is required']
        
        if not phone_number:
            errors['phone_number'] = ['This field is required']
        elif len(phone_number) < 10:
            errors['phone_number'] = ['Phone number must be at least 10 digits']
        
        if not password:
            errors['password'] = ['This field is required']
        elif len(password) < 8:
            errors['password'] = ['Password must be at least 8 characters long']
        
        # If there are validation errors, return them
        if errors:
            return JsonResponse({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }, status=400)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role='user'  # Default role
        )
            
        # Return success response (no tokens - user must login)
        return JsonResponse({
                'success': True,
            'message': 'Account created successfully. Please login to continue.',
                'data': {
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    'phone_number': user.phone_number,
                    'profile_picture_url': None  # New users don't have profile picture yet
                    }
                }
        }, status=201)
            
    except Exception as e:
        # Handle unexpected errors
        return JsonResponse({
            'success': False,
            'message': 'Server error occurred',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def login_api(request):
    """API endpoint for user login"""
    try:
        # Parse request data based on content type
        content_type = request.content_type
        if content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data',
                    'errors': {'json': ['Request body contains invalid JSON']}
                }, status=400)
        else:
            # Handle form data
            data = request.POST.dict()
        
        # Validate required fields
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({
                'success': False,
                'message': 'Missing credentials',
                'errors': {
                    'credentials': ['Both username and password are required']
                }
            }, status=400)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if user is not None:
            if user.is_active:
                # Create OTP for login verification
                otp_result = create_otp(user, purpose='login')
                
                if not otp_result['email_sent']:
                    return JsonResponse({
                        'success': False,
                        'message': 'Failed to send OTP email',
                        'errors': {
                            'email': ['Could not send verification code. Please try again.']
                        }
                    }, status=500)
                
                # Return session_id for OTP verification
                return JsonResponse({
                    'success': True,
                    'message': 'OTP sent to your email. Please verify to complete login.',
                    'data': {
                        'session_id': otp_result['session_id'],
                            'email': user.email,
                        'expires_in': 300  # 5 minutes in seconds
                    }
                }, status=200)
                    
            else:
                # User account is disabled
                return JsonResponse({
                    'success': False,
                    'message': 'Account disabled',
                    'errors': {
                        'account': ['This account has been disabled. Please contact support.']
                    }
                }, status=403)
        else:
            # Invalid credentials
            return JsonResponse({
                'success': False,
                'message': 'Invalid credentials',
                'errors': {
                    'credentials': ['Username or password is incorrect']
                }
            }, status=401)
            
    except Exception as e:
        # Handle unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Login API error: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'message': 'Internal server error',
            'errors': {
                'server': ['An unexpected error occurred during login']
            }
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_login_otp_api(request):
    """API endpoint to verify OTP and complete login"""
    try:
        # Parse request data
        content_type = request.content_type
        if content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data',
                    'errors': {'json': ['Request body contains invalid JSON']}
                }, status=400)
        else:
            data = request.POST.dict()
        
        # Validate required fields
        session_id = data.get('session_id')
        otp_code = data.get('otp_code')
        
        if not session_id or not otp_code:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields',
                'errors': {
                    'fields': ['Both session_id and otp_code are required']
                }
            }, status=400)
        
        # Find the OTP record by session_id
        try:
            otp_record = OTPVerification.objects.get(
                session_id=session_id,
                purpose='login',
                is_used=False
            )
        except OTPVerification.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid or expired session',
                'errors': {
                    'session': ['Login session not found or has expired']
                }
            }, status=400)
        
        # Get user from OTP record
        user = otp_record.user
        
        # Verify OTP
        verification_result = verify_otp_util(user, otp_code, purpose='login', session_id=session_id)
        
        if not verification_result['valid']:
            return JsonResponse({
                'success': False,
                'message': 'OTP verification failed',
                'errors': {
                    'otp': [verification_result.get('error', 'Invalid OTP code')]
                }
            }, status=400)
        
        # OTP verified successfully - update last login and generate tokens
        from django.contrib.auth.models import update_last_login
        update_last_login(None, user)
        
        # Generate JWT tokens
        tokens = get_tokens_for_user(user)
        
        # Return successful login response with tokens
        return JsonResponse({
            'success': True,
            'message': 'Login successful',
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_vendor_role': user.is_vendor_role,
                    'phone_number': getattr(user, 'phone_number', '') or '',
                    'profile_picture_url': user.profile_picture.url if user.profile_picture else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                },
                'tokens': {
                    'access': tokens['access'],
                    'refresh': tokens['refresh'],
                }
            }
        }, status=200)
        
    except Exception as e:
        # Handle unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Verify login OTP error: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'message': 'Internal server error',
            'errors': {
                'server': ['An unexpected error occurred during OTP verification']
            }
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def logout_api(request):
    """API endpoint for user logout"""
    # For JWT tokens, logout is handled client-side by removing tokens
    # But we can still clear session if it exists
    auth_logout(request)
    return JsonResponse({
        'success': True,
        'message': 'Logout successful. Please remove tokens from client storage.'
    }, status=200)


@csrf_exempt
@require_http_methods(['POST'])
def refresh_token_api(request):
    """API endpoint to refresh access token using refresh token"""
    try:
        # Parse request data
        content_type = request.content_type
        if content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data',
                    'errors': {'json': ['Request body contains invalid JSON']}
                }, status=400)
        else:
            data = request.POST.dict()
        
        refresh_token = data.get('refresh')
        if not refresh_token:
            return JsonResponse({
                'success': False,
                'message': 'Missing refresh token',
                'errors': {'refresh': ['Refresh token is required']}
            }, status=400)
        
        # Refresh the token
        try:
            new_tokens = refresh_access_token(refresh_token)
            
            return JsonResponse({
                'success': True,
                'message': 'Token refreshed successfully',
                'data': {
                    'access': new_tokens['access']
                }
            }, status=200)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Invalid or expired refresh token',
                'errors': {'refresh': [str(e)]}
            }, status=401)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Internal server error',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['GET'])
def dashboard_api(request):
    """API endpoint for dashboard data with filtering, sorting, and pagination"""
    try:
        # Authentication - support both session and token auth
        if request.user.is_authenticated:
            user = request.user
        else:
            user = get_token_user(request)
            if not user:
                return JsonResponse({
                    'success': False,
                    'message': 'Authentication required',
                    'errors': {'auth': ['Please provide valid authentication credentials']}
                }, status=401)
        
        # Get filter parameters from the request
        search_query = request.GET.get('q', '').strip()
        category = request.GET.get('category', '')
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')
        sort_by = request.GET.get('sort', 'newest')
        page_number = request.GET.get('page', 1)
        page_size = int(request.GET.get('page_size', 20))  # Allow custom page size
        
        # Validate page_size (limit to reasonable values)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 20
        
        # Start with all products (no job posts anymore)
        posts = Post.objects.all()
        
        # Filter out sold-out products (inventory must be greater than 0)
        posts = posts.filter(inventory__gt=0)
        
        # Filter out the user's own products if they are a vendor
        if user.is_vendor_role:
            posts = posts.exclude(user=user)
        
        # Apply search filter if provided
        if search_query:
            # Split search query into individual words for better matching
            search_words = search_query.strip().split()
            
            # Build query for each word (all words must match at least one field)
            search_filter = Q()
            for word in search_words:
                word_filter = Q()
                word_filter |= Q(title__icontains=word)
                word_filter |= Q(description__icontains=word)
                word_filter |= Q(user__username__icontains=word)
                word_filter |= Q(user__first_name__icontains=word)
                word_filter |= Q(user__last_name__icontains=word)
                word_filter |= Q(category__name__icontains=word)
                search_filter &= word_filter  # AND all words together
            
            posts = posts.filter(search_filter)
        
        # Apply category filter if provided
        if category:
            # Try to filter by category ID first, then by slug
            try:
                category_id = int(category)
                posts = posts.filter(category__id=category_id, category__is_active=True)
            except (ValueError, TypeError):
                # Try by slug
                posts = posts.filter(category__slug=category, category__is_active=True)
        
        # Apply price range filters
        if min_price:
            try:
                posts = posts.filter(price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                posts = posts.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        # Apply sorting
        if sort_by == 'price_low':
            posts = posts.order_by('price')
        elif sort_by == 'price_high':
            posts = posts.order_by('-price')
        elif sort_by == 'popular':
            posts = posts.order_by('-total_purchases', '-created_at')
        elif sort_by == 'rating':
            # Order by average rating (implement this later)
            posts = posts.order_by('-created_at')
        else:  # newest (default)
            posts = posts.order_by('-created_at')
        
        # Get total count before pagination
        total_products = posts.count()
        
        # Get user's bookmarked posts
        bookmarked_posts = [bookmark.post.id for bookmark in Bookmark.objects.filter(user=user)]
        
        # Get user's liked posts
        liked_posts = [post.id for post in Post.objects.filter(likes=user)]
        
        # Pagination
        paginator = Paginator(posts, page_size)
        try:
            page_obj = paginator.get_page(page_number)
        except Exception:
            page_obj = paginator.get_page(1)
        
        # Convert posts to JSON-serializable format
        posts_data = []
        for post in page_obj:
            # Get auxiliary images
            auxiliary_images = ProductImage.objects.filter(product=post).order_by('display_order')
            aux_images_data = []
            for img in auxiliary_images:
                aux_images_data.append({
                    'id': img.id,
                    'image_url': img.image.url if img.image else None,
                    'display_order': img.display_order
                })
            
            # Calculate average rating if reviews exist
            reviews = ProductReview.objects.filter(product=post)
            avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
            avg_rating = round(avg_rating, 1) if avg_rating else None
            
            # Serialize category
            category_data = None
            if post.category:
                category_data = {
                    'id': post.category.id,
                    'name': post.category.name,
                    'slug': post.category.slug,
                    'category_image': post.category.category_image.url if post.category.category_image else None
                }
            
            post_data = {
                'id': post.id,
                'title': post.title,
                'description': post.description,
                'price': float(post.price) if post.price else None,
                'is_great_deal': post.is_great_deal,
                'original_price': float(post.original_price) if post.original_price else None,
                'discount_percentage': post.discount_percentage() if post.is_great_deal else None,
                'savings_amount': float(post.savings_amount()) if post.is_great_deal else None,
                'category': category_data,
                'inventory': post.inventory,
                'created_at': post.created_at.isoformat(),
                'updated_at': post.updated_at.isoformat(),
                'total_purchases': post.total_purchases,
                'image_url': post.image.url if post.image else None,
                'auxiliary_images': aux_images_data,
                'average_rating': avg_rating,
                'review_count': reviews.count(),
                'total_likes': post.total_likes(),
                'is_bookmarked': post.id in bookmarked_posts,
                'is_liked': post.id in liked_posts,
                'user': {
                    'id': post.user.id,
                    'username': post.user.username,
                    'first_name': post.user.first_name,
                    'last_name': post.user.last_name,
                    'is_vendor_role': post.user.is_vendor_role,
                    'profile_picture_url': post.user.profile_picture.url if post.user.profile_picture else None
                }
            }
            posts_data.append(post_data)
        
        # Get all categories for the filter dropdown
        from posts.models import Category
        categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
        categories_data = []
        for cat in categories:
            categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'category_image': cat.category_image.url if cat.category_image else None
            })
        
        # Build response
        response_data = {
            'success': True,
            'message': 'Dashboard data retrieved successfully',
            'data': {
                'posts': posts_data,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'page_size': page_size,
                    'total_items': total_products,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                    'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                    'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None
                },
                'filters': {
                    'search_query': search_query,
                    'selected_category': category,
                    'min_price': min_price,
                    'max_price': max_price,
                    'sort_by': sort_by,
                    'available_categories': categories_data,
                    'available_sorts': [
                        {'value': 'newest', 'label': 'Newest First'},
                        {'value': 'price_low', 'label': 'Price: Low to High'},
                        {'value': 'price_high', 'label': 'Price: High to Low'},
                        {'value': 'popular', 'label': 'Most Popular'},
                        {'value': 'rating', 'label': 'Highest Rated'}
                    ]
                },
                'user_info': {
                    'id': user.id,
                    'username': user.username,
                    'is_vendor_role': user.is_vendor_role,
                    'total_bookmarks': len(bookmarked_posts),
                    'total_liked_posts': len(liked_posts)
                },
                'summary': {
                    'total_products': total_products,
                    'products_on_page': len(posts_data),
                    'search_applied': bool(search_query),
                    'filters_applied': bool(category or min_price or max_price),
                    'sort_applied': sort_by != 'newest'
                }
            }
        }
        
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Dashboard API error: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        
        return JsonResponse({
            'success': False,
            'message': 'Internal server error',
            'errors': {'server': ['An unexpected error occurred']}
        }, status=500)


@csrf_exempt
@require_http_methods(['GET'])
def agaseke_dashboard_api(request):
    """API endpoint to get agaseke dashboard data"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Ensure user is agaseke
        if not user.is_agaseke():
            return JsonResponse({
                'success': False,
                'message': 'agaseke role required',
                'errors': {'role': ['You need to be an agaseke operator to access this dashboard']}
            }, status=403)
        
        # Get all purchases awaiting pickup
        awaiting_purchases = Purchase.objects.filter(
            status='awaiting_pickup'
        ).select_related('buyer', 'product', 'product__user').order_by('-created_at')
        
        # Get all purchases awaiting delivery
        awaiting_deliveries = Purchase.objects.filter(
            status='awaiting_delivery'
        ).select_related('buyer', 'product', 'product__user').order_by('-created_at')
        
        # Get orders out for delivery
        out_for_delivery = Purchase.objects.filter(
            status='out_for_delivery'
        ).select_related('buyer', 'product', 'product__user').order_by('-created_at')
        
        # Get completed purchases for revenue tracking
        completed_purchases = Purchase.objects.filter(
            status='completed',
            agaseke_user=user
        ).select_related('buyer', 'product')
        
        # Calculate revenue statistics
        total_commission = completed_purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
        
        monthly_commission = completed_purchases.filter(
            pickup_confirmed_at__month=timezone.now().month,
            pickup_confirmed_at__year=timezone.now().year
        ).aggregate(total=Sum('agaseke_commission_amount'))['total'] or 0
        
        # Serialize purchases
        from authentication.serializers_helpers import serialize_purchase, serialize_user
        awaiting_purchases_data = [serialize_purchase(p) for p in awaiting_purchases[:20]]
        awaiting_deliveries_data = [serialize_purchase(p) for p in awaiting_deliveries[:20]]
        out_for_delivery_data = [serialize_purchase(p) for p in out_for_delivery[:20]]
        completed_purchases_data = [serialize_purchase(p) for p in completed_purchases[:20]]
        
        return JsonResponse({
            'success': True,
            'message': 'agaseke dashboard data retrieved successfully',
            'data': {
                'operator': serialize_user(user),
                'statistics': {
                    'awaiting_pickup_count': awaiting_purchases.count(),
                    'awaiting_delivery_count': awaiting_deliveries.count(),
                    'out_for_delivery_count': out_for_delivery.count(),
                    'total_completed': completed_purchases.count(),
                    'total_commission': float(total_commission) if total_commission else 0.0,
                    'monthly_commission': float(monthly_commission) if monthly_commission else 0.0,
                },
                'awaiting_pickup': awaiting_purchases_data,
                'awaiting_delivery': awaiting_deliveries_data,
                'out_for_delivery': out_for_delivery_data,
                'completed_purchases': completed_purchases_data,
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving agaseke dashboard',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def user_qr_code_api(request):
    """
    API endpoint to get user's QR code in base64 format
    
    GET - Get existing QR code
    POST - Generate/refresh QR code
    
    Returns QR code as base64 string
    """
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Generate or update QR code
        from .qr_utils import update_user_qr_code
        import base64
        from io import BytesIO
        
        # Update/create QR code for the user
        user_qr = update_user_qr_code(user)
        
        # Read the QR code image and convert to base64
        qr_image_base64 = None
        if user_qr.qr_image:
            try:
                # Read the image file
                user_qr.qr_image.open('rb')
                image_data = user_qr.qr_image.read()
                user_qr.qr_image.close()
                
                # Convert to base64
                qr_image_base64 = base64.b64encode(image_data).decode('utf-8')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error reading QR image: {str(e)}")
        
        # Get pending purchases count
        pending_purchases = Purchase.objects.filter(
            buyer=user,
            status__in=['awaiting_pickup', 'awaiting_delivery']
        )
        
        return JsonResponse({
            'success': True,
            'message': 'QR code generated successfully',
            'data': {
                'qr_code_base64': qr_image_base64,  # Base64 encoded PNG image
                'qr_code_data': user_qr.qr_data,    # Raw QR data (JWT token)
                'expires_at': user_qr.expires_at.isoformat(),
                'pending_purchases_count': pending_purchases.count(),
                'image_format': 'png',
                'encoding': 'base64'
            }
        }, status=200)
        
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"QR code API error: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'message': 'Error generating QR code',
            'errors': {'server': [str(e)]}
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def get_purchases_by_qr(request):
    """API endpoint to get purchases from a QR code"""
    # Get user from token (for API authentication)
    user = get_token_user(request)
    if not user:
        return JsonResponse({
            'error': 'Authentication required',
            'purchases': []
        }, status=401)
    
    if not user.is_agaseke():
        return JsonResponse({'error': 'Access denied. agaseke role required.', 'purchases': []}, status=403)
    
    try:
        data = json.loads(request.body)
        qr_data = data.get('qr_data')
        
        if not qr_data:
            return JsonResponse({'error': 'No QR data provided', 'purchases': []}, status=400)
        
                # Decode QR data
                decoded_data = decode_qr_data(qr_data.strip())
                
                if isinstance(decoded_data, dict) and 'error' in decoded_data:
            return JsonResponse({'error': decoded_data['error'], 'purchases': []}, status=400)
                
                # Get purchase information
                purchase_info = get_user_purchases_from_qr(decoded_data)
                
                # If no purchases found or empty QR data
                if not purchase_info.get('purchases'):
            # Still return user info if possible
            user_info = {}
            try:
                user = User.objects.get(id=purchase_info.get('user_id'))
                user_info = {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email
                }
            except Exception:
                pass
            return JsonResponse({
                'error': 'No pending purchases found in this QR code.',
                'purchases': [],
                'buyer': user_info
            }, status=404)
        
        # Add buyer information
        try:
            user = User.objects.get(id=purchase_info['user_id'])
            purchase_info['buyer'] = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found', 'purchases': []}, status=404)
        
        # Always include purchases key
        if 'purchases' not in purchase_info:
            purchase_info['purchases'] = []
        
        return JsonResponse(purchase_info)
    except Exception as e:
        import traceback
        print('Error in get_purchases_by_qr:', traceback.format_exc())
        return JsonResponse({'error': f'Error processing request: {str(e)}', 'purchases': []}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def verify_buyer_credentials(request):
    """API endpoint to verify buyer credentials"""
    # Get user from token (for API authentication)
    user = get_token_user(request)
    if not user:
        return JsonResponse({
            'error': 'Authentication required'
        }, status=401)
    
    if not user.is_agaseke():
        return JsonResponse({'error': 'Access denied. agaseke role required.'}, status=403)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        user_id = data.get('user_id')  # This should match the user from the QR code
        
        if not all([username, password, user_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Verify credentials
        user = authenticate(username=username, password=password)
        
        if not user:
            return JsonResponse({'error': 'Invalid username or password'}, status=401)
        
        # Ensure the authenticated user matches the user from the QR code
        if user.id != int(user_id):
            return JsonResponse({'error': 'Authentication failed. User mismatch.'}, status=401)
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
            except Exception as e:
        return JsonResponse({'error': f'Error processing request: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def send_otp(request):
    """API endpoint to send OTP for purchase verification"""
    # Get user from token (for API authentication)
    user = get_token_user(request)
    if not user:
        return JsonResponse({
            'error': 'Authentication required'
        }, status=401)
    
    if not user.is_agaseke():
        return JsonResponse({'error': 'Access denied. agaseke role required.'}, status=403)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        purchase_id = data.get('purchase_id')
        
        if not user_id:
            return JsonResponse({'error': 'Missing user_id'}, status=400)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Create and send OTP
        otp_result = create_otp(user, 'purchase_confirmation')
        print(otp_result)
        
        if not otp_result.get('email_sent'):
            return JsonResponse({'error': 'Failed to send OTP email'}, status=500)
            
            return JsonResponse({
                'success': True,
            'message': f'OTP sent to {user.email}',
            'session_id': otp_result.get('otp_id')
        })
    except Exception as e:
        return JsonResponse({'error': f'Error processing request: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def verify_otp_view(request):
    """API endpoint to verify OTP for purchase confirmation"""
    # Get user from token (for API authentication)
    user = get_token_user(request)
    if not user:
                return JsonResponse({
            'error': 'Authentication required'
        }, status=401)
    
    if not user.is_agaseke():
        return JsonResponse({'error': 'Access denied. agaseke role required.'}, status=403)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        otp_code = data.get('otp_code')
        purchase_id = data.get('purchase_id')
        
        if not all([user_id, otp_code]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Verify OTP using the utility function
        otp_result = verify_otp_util(user, otp_code, 'purchase_confirmation')
        
        if not otp_result.get('valid'):
            return JsonResponse({'error': otp_result.get('error', 'Invalid OTP')}, status=400)
        
                return JsonResponse({
            'success': True,
            'message': 'OTP verified successfully',
            'purchase_id': purchase_id  # Include purchase_id in response for frontend
        })
    except Exception as e:
        return JsonResponse({'error': f'Error processing request: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def complete_purchase_pickup(request):
    """API endpoint to complete purchase pickup after OTP verification"""
    # Get user from token (for API authentication)
    agaseke_user = get_token_user(request)
    if not agaseke_user:
        return JsonResponse({
            'error': 'Authentication required'
        }, status=401)
    
    if not agaseke_user.is_agaseke():
        return JsonResponse({'error': 'Access denied. agaseke role required.'}, status=403)
    
    try:
        data = json.loads(request.body)
        purchase_id = data.get('purchase_id')
        
        print(f"DEBUG: Received purchase completion request with purchase_id: {purchase_id}")
        print(f"DEBUG: Request data: {data}")
        
        if not purchase_id:
            print("DEBUG: Missing purchase_id in request")
            return JsonResponse({'error': 'Missing purchase_id'}, status=400)
        
        try:
            purchase = Purchase.objects.get(id=purchase_id)
            print(f"DEBUG: Found purchase with ID {purchase_id}")
            print(f"DEBUG: Purchase status: {purchase.status}")
            print(f"DEBUG: Purchase details: Order ID: {purchase.order_id}, Product: {purchase.product.title}")
        except Purchase.DoesNotExist:
            print(f"DEBUG: Purchase with ID {purchase_id} not found")
            return JsonResponse({'error': 'Purchase not found'}, status=404)
        
        # Check if purchase is awaiting pickup or delivery
        if purchase.status not in ['awaiting_pickup', 'awaiting_delivery']:
            print(f"DEBUG: Invalid purchase status. Expected 'awaiting_pickup' or 'awaiting_delivery', got '{purchase.status}'")
            return JsonResponse({'error': f'Invalid purchase status: {purchase.status}. Expected: awaiting_pickup or awaiting_delivery'}, status=400)
            
            # Complete the purchase
            purchase.status = 'completed'
        purchase.agaseke_user = agaseke_user
            purchase.pickup_confirmed_at = timezone.now()
            purchase.save()
            
            # Update vendor and buyer stats
            vendor = purchase.product.user
            vendor.total_sales += purchase.vendor_payment_amount
            vendor.save()
            
            buyer = purchase.buyer
            buyer.total_purchases += (purchase.purchase_price * purchase.quantity)
            buyer.save()
            
        # Regenerate buyer's QR code to remove completed purchase
        try:
            from .qr_utils import update_user_qr_code
            update_user_qr_code(buyer)
            print(f"DEBUG: Updated QR code for buyer {buyer.username}")
        except Exception as e:
            print(f"DEBUG: Failed to update QR code for buyer: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'message': 'Purchase confirmed successfully!',
                'vendor_payment': str(purchase.vendor_payment_amount),
                'agaseke_commission': str(purchase.agaseke_commission_amount)
            })
    except Exception as e:
        return JsonResponse({'error': f'Error processing request: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def complete_purchases_bulk(request):
    """API endpoint to complete multiple purchases at once after OTP verification"""
    # Get user from token (for API authentication)
    agaseke_user = get_token_user(request)
    if not agaseke_user:
        return JsonResponse({
            'error': 'Authentication required',
            'completed': [],
            'failed': []
        }, status=401)
    
    if not agaseke_user.is_agaseke():
        return JsonResponse({
            'error': 'Access denied. agaseke role required.',
            'completed': [],
            'failed': []
        }, status=403)
    
    try:
        from django.db import transaction
        from decimal import Decimal
        
        data = json.loads(request.body)
        purchase_ids = data.get('purchase_ids', [])
        
        if not purchase_ids:
            return JsonResponse({
                'error': 'No purchase IDs provided',
                'completed': [],
                'failed': []
            }, status=400)
        
        if not isinstance(purchase_ids, list):
            return JsonResponse({
                'error': 'purchase_ids must be an array',
                'completed': [],
                'failed': []
            }, status=400)
        
        # Fetch all purchases
        purchases = Purchase.objects.filter(id__in=purchase_ids).select_related('buyer', 'product', 'product__user')
        
        if not purchases.exists():
            return JsonResponse({
                'error': 'No valid purchases found',
                'completed': [],
                'failed': []
            }, status=404)
        
        # Validate all purchases belong to the same buyer
        buyer_ids = set(p.buyer_id for p in purchases)
        if len(buyer_ids) > 1:
                return JsonResponse({
                'error': 'All purchases must belong to the same buyer',
                'completed': [],
                'failed': []
            }, status=400)
        
        # Validate all purchases are in valid status
        completed_purchases = []
        failed_purchases = []
        total_vendor_payment = Decimal('0.00')
        total_agaseke_commission = Decimal('0.00')
        
        # Use atomic transaction to ensure all-or-nothing completion
        with transaction.atomic():
            for purchase in purchases:
                try:
                    # Check if purchase is awaiting pickup or delivery
                    if purchase.status not in ['awaiting_pickup', 'awaiting_delivery']:
                        failed_purchases.append({
                            'purchase_id': purchase.id,
                            'order_id': purchase.order_id,
                            'error': f'Invalid status: {purchase.status}',
                            'product': purchase.product.title
                        })
                        continue
                    
                    # Complete the purchase
            purchase.status = 'completed'
                    purchase.agaseke_user = agaseke_user
                    purchase.pickup_confirmed_at = timezone.now()
            purchase.save()
            
                    # Update vendor stats
            vendor = purchase.product.user
            vendor.total_sales += purchase.vendor_payment_amount
            vendor.save()
            
                    # Track totals
                    total_vendor_payment += purchase.vendor_payment_amount
                    total_agaseke_commission += purchase.agaseke_commission_amount
                    
                    completed_purchases.append({
                        'purchase_id': purchase.id,
                        'order_id': purchase.order_id,
                        'product': purchase.product.title,
                'vendor_payment': str(purchase.vendor_payment_amount),
                'agaseke_commission': str(purchase.agaseke_commission_amount)
            })
    
                except Exception as e:
                    failed_purchases.append({
                        'purchase_id': purchase.id,
                        'order_id': getattr(purchase, 'order_id', 'N/A'),
                        'error': str(e),
                        'product': getattr(purchase.product, 'title', 'Unknown')
                    })
            
            # If at least one purchase was completed, update buyer stats
            if completed_purchases:
                buyer = purchases.first().buyer
                total_buyer_spent = sum(p.purchase_price * p.quantity for p in purchases if p.status == 'completed')
                buyer.total_purchases += total_buyer_spent
                buyer.save()
        
        # Regenerate buyer's QR code to remove completed purchases
        if completed_purchases:
            try:
                from .qr_utils import update_user_qr_code
                buyer = purchases.first().buyer
                update_user_qr_code(buyer)
            except Exception as e:
                print(f"Failed to update QR code for buyer: {str(e)}")
        
        # Prepare response
        response_data = {
            'success': len(completed_purchases) > 0,
            'message': f'Completed {len(completed_purchases)} out of {len(purchase_ids)} purchases',
            'summary': {
                'total_completed': len(completed_purchases),
                'total_failed': len(failed_purchases),
                'total_vendor_payment': str(total_vendor_payment),
                'total_agaseke_commission': str(total_agaseke_commission)
            },
            'completed': completed_purchases,
            'failed': failed_purchases
        }
        
        # Determine HTTP status code
        if len(completed_purchases) == len(purchase_ids):
            status_code = 200  # All succeeded
        elif len(completed_purchases) > 0:
            status_code = 207  # Partial success (Multi-Status)
        else:
            status_code = 400  # All failed
        
        return JsonResponse(response_data, status=status_code)
        
    except Exception as e:
        import traceback
        print('Error in complete_purchases_bulk:', traceback.format_exc())
        return JsonResponse({
            'error': f'Error processing request: {str(e)}',
            'completed': [],
            'failed': []
        }, status=500)

@csrf_exempt
def get_vendor_statistics_modal(request, vendor_id):
    """API endpoint to get vendor statistics for modal popup"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if not request.user.is_authenticated or not request.user.is_agaseke():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Get the vendor
        vendor = User.objects.get(id=vendor_id, is_vendor_role=True)
        
        # Get all purchases for this vendor
        purchases = Purchase.objects.filter(
            product__user=vendor,
            status='completed'
        ).select_related('product', 'buyer', 'agaseke_user')
        
        # Calculate vendor statistics
        total_sales = purchases.count()
        total_revenue = purchases.aggregate(
            total=Sum('vendor_payment_amount')
        )['total'] or 0
        
        # Monthly statistics
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_purchases = purchases.filter(
            pickup_confirmed_at__month=current_month,
            pickup_confirmed_at__year=current_year
        )
        monthly_revenue = monthly_purchases.aggregate(
            total=Sum('vendor_payment_amount')
        )['total'] or 0
        
        # Product-wise breakdown
        product_stats = list(purchases.values('product__title').annotate(
            total_sales=Count('id'),
            total_revenue=Sum('vendor_payment_amount'),
            avg_price=Avg('vendor_payment_amount')
        ).order_by('-total_revenue')[:5])  # Limit to top 5 products
        
        # agaseke commission from this vendor
        agaseke_commission = purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
        
        # Monthly agaseke commission
        monthly_agaseke_commission = monthly_purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
        
        # Recent transactions
        recent_transactions = list(purchases.order_by('-pickup_confirmed_at')[:5].values(
            'product__title', 'buyer__username', 'order_id', 'quantity', 
            'vendor_payment_amount', 'pickup_confirmed_at', 'created_at'
        ))
        
        # Commission breakdown
        total_product_price = purchases.aggregate(total=Sum('purchase_price'))['total'] or 0
        total_delivery_fees = purchases.aggregate(total=Sum('delivery_fee'))['total'] or 0
        
        commission_breakdown = {
            'vendor_earnings': float(total_revenue),
            'agaseke_commission': float(agaseke_commission),
            'product_commission': float(total_product_price * Decimal('0.2')),
            'delivery_fees': float(total_delivery_fees),
            'total_transaction_value': float(total_product_price + total_delivery_fees)
        }
        
        # Format dates for JSON serialization
        for transaction in recent_transactions:
            if transaction['pickup_confirmed_at']:
                transaction['pickup_confirmed_at'] = transaction['pickup_confirmed_at'].strftime('%b %d, %H:%M')
            else:
                transaction['pickup_confirmed_at'] = transaction['created_at'].strftime('%b %d, %H:%M')
            transaction['created_at'] = transaction['created_at'].strftime('%b %d, %H:%M')
        
        data = {
            'vendor': {
                'id': vendor.id,
                'username': vendor.username,
                'email': vendor.email
            },
            'statistics': {
                'total_sales': total_sales,
                'total_revenue': float(total_revenue),
                'monthly_revenue': float(monthly_revenue),
                'monthly_sales': monthly_purchases.count(),
                'agaseke_commission': float(agaseke_commission),
                'monthly_agaseke_commission': float(monthly_agaseke_commission),
                'commission_rate': 80,
                'agaseke_rate': 20
            },
            'product_stats': product_stats,
            'recent_transactions': recent_transactions,
            'commission_breakdown': commission_breakdown
        }
        
        return JsonResponse(data)
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'Vendor not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['GET'])
def get_all_vendors_api(request):
    """API endpoint for agaseke agents to get list of all vendors"""
    # Get user from token (for API authentication)
        user = get_token_user(request)
        if not user:
            return JsonResponse({
            'error': 'Authentication required'
            }, status=401)
        
    if not user.is_agaseke():
        return JsonResponse({'error': 'Access denied. agaseke role required.'}, status=403)
    
    try:
        from django.core.paginator import Paginator
        
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 per page
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', '-total_sales')  # Default: highest sales first
        
        # Get all vendors
        vendors = User.objects.filter(is_vendor_role=True)
        
        # Apply search filter
        if search_query:
            from django.db.models import Q
            vendors = vendors.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        # Apply sorting
        valid_sorts = ['total_sales', '-total_sales', 'username', '-username', 'date_joined', '-date_joined']
        if sort_by in valid_sorts:
            vendors = vendors.order_by(sort_by)
        else:
            vendors = vendors.order_by('-total_sales')
        
        # Paginate
        paginator = Paginator(vendors, limit)
        page_obj = paginator.get_page(page)
        
        # Serialize vendor data
        vendors_data = []
        for vendor in page_obj:
            # Get vendor statistics
            vendor_purchases = Purchase.objects.filter(
                product__user=vendor,
                status='completed'
            )
            
            total_sales = vendor_purchases.count()
            total_products = Post.objects.filter(user=vendor).count()
            in_stock_products = Post.objects.filter(user=vendor, inventory__gt=0).count()
            
            # Calculate monthly stats
            current_month = timezone.now().month
            current_year = timezone.now().year
            monthly_sales = vendor_purchases.filter(
                pickup_confirmed_at__month=current_month,
                pickup_confirmed_at__year=current_year
            ).count()
            
            vendors_data.append({
                'id': vendor.id,
                'username': vendor.username,
                'first_name': vendor.first_name,
                'last_name': vendor.last_name,
                'email': vendor.email,
                'phone_number': vendor.phone_number,
                'profile_picture': vendor.profile_picture.url if vendor.profile_picture else None,
                'date_joined': vendor.date_joined.isoformat(),
                'statistics': {
                    'total_sales': total_sales,
                    'total_revenue': float(vendor.total_sales),
                    'total_products': total_products,
                    'in_stock_products': in_stock_products,
                    'monthly_sales': monthly_sales
                }
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'vendors': vendors_data,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'total_vendors': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            }
        })
        
    except Exception as e:
        import traceback
        print('Error in get_all_vendors_api:', traceback.format_exc())
        return JsonResponse({'error': f'Error processing request: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(['GET'])
def get_vendor_profile_api(request, vendor_id):
    """API endpoint for agaseke agents to get detailed vendor profile"""
    # Get user from token (for API authentication)
    user = get_token_user(request)
    if not user:
        return JsonResponse({
            'error': 'Authentication required'
        }, status=401)
    
    if not user.is_agaseke():
        return JsonResponse({'error': 'Access denied. agaseke role required.'}, status=403)
    
    try:
        # Get the vendor
        vendor = User.objects.get(id=vendor_id, is_vendor_role=True)
        
        # Get all purchases for this vendor
        purchases = Purchase.objects.filter(
            product__user=vendor,
            status='completed'
        ).select_related('product', 'buyer', 'agaseke_user')
        
        # Calculate vendor statistics
        total_sales = purchases.count()
        total_revenue = purchases.aggregate(
            total=Sum('vendor_payment_amount')
        )['total'] or 0
        
        # Monthly statistics
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_purchases = purchases.filter(
            pickup_confirmed_at__month=current_month,
            pickup_confirmed_at__year=current_year
        )
        monthly_revenue = monthly_purchases.aggregate(
            total=Sum('vendor_payment_amount')
        )['total'] or 0
        monthly_sales = monthly_purchases.count()
        
        # Product statistics
        all_products = Post.objects.filter(user=vendor)
        total_products = all_products.count()
        in_stock_products = all_products.filter(inventory__gt=0).count()
        out_of_stock_products = all_products.filter(inventory=0).count()
        
        # Product-wise breakdown (top 10 products)
        product_stats = list(purchases.values('product__id', 'product__title').annotate(
            total_sales=Count('id'),
            total_revenue=Sum('vendor_payment_amount'),
            total_quantity=Sum('quantity')
        ).order_by('-total_revenue')[:10])
        
        # agaseke commission from this vendor
        agaseke_commission = purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
        
        # Monthly agaseke commission
        monthly_agaseke_commission = monthly_purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
        
        # Recent transactions (last 20)
        recent_transactions = []
        for purchase in purchases.order_by('-pickup_confirmed_at')[:20]:
            recent_transactions.append({
                'purchase_id': purchase.id,
                'order_id': purchase.order_id,
                'product_title': purchase.product.title,
                'buyer_username': purchase.buyer.username,
                'quantity': purchase.quantity,
                'vendor_payment': str(purchase.vendor_payment_amount),
                'agaseke_commission': str(purchase.agaseke_commission_amount),
                'pickup_confirmed_at': purchase.pickup_confirmed_at.isoformat() if purchase.pickup_confirmed_at else None,
                'created_at': purchase.created_at.isoformat()
            })
        
        # Weekly sales trend (last 7 days)
        from datetime import timedelta
        today = timezone.now().date()
        weekly_trend = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_purchases = purchases.filter(
                pickup_confirmed_at__date=day
            )
            weekly_trend.append({
                'date': day.isoformat(),
                'sales': day_purchases.count(),
                'revenue': float(day_purchases.aggregate(total=Sum('vendor_payment_amount'))['total'] or 0)
            })
        
        # Get vendor's products (limited to 10 recent)
        from authentication.serializers_helpers import serialize_post
        recent_products = all_products.order_by('-created_at')[:10]
        products_data = [serialize_post(product, user) for product in recent_products]
        
        # Build response
        data = {
            'success': True,
            'data': {
                'vendor': {
                    'id': vendor.id,
                    'username': vendor.username,
                    'first_name': vendor.first_name,
                    'last_name': vendor.last_name,
                    'email': vendor.email,
                    'phone_number': vendor.phone_number,
                    'profile_picture': vendor.profile_picture.url if vendor.profile_picture else None,
                    'date_joined': vendor.date_joined.isoformat(),
                    'is_vendor': True
                },
                'statistics': {
                    'total_sales': total_sales,
                    'total_revenue': str(total_revenue),
                    'monthly_sales': monthly_sales,
                    'monthly_revenue': str(monthly_revenue),
                    'total_products': total_products,
                    'in_stock_products': in_stock_products,
                    'out_of_stock_products': out_of_stock_products,
                    'agaseke_commission': str(agaseke_commission),
                    'monthly_agaseke_commission': str(monthly_agaseke_commission)
                },
                'top_products': product_stats,
                'recent_transactions': recent_transactions,
                'weekly_trend': weekly_trend,
                'recent_products': products_data
            }
        }
        
        return JsonResponse(data)
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'Vendor not found'}, status=404)
    except Exception as e:
        import traceback
        print('Error in get_vendor_profile_api:', traceback.format_exc())
        return JsonResponse({'error': f'Error processing request: {str(e)}'}, status=500)
