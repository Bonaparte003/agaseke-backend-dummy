import os
import csv
import io
import json
from datetime import datetime
from decimal import Decimal
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from users.forms import SignUpForm
from posts.forms import ProductReviewForm
from users.models import User
from posts.models import Post, ProductReview, Bookmark
from products.models import Purchase, ProductImage
from .models import UserQRCode, OTPVerification
from .qr_utils import update_user_qr_code, decode_qr_data, get_user_purchases_from_qr
from .otp_utils import create_otp, verify_otp
from .jwt_utils import get_tokens_for_user, get_user_from_token, refresh_access_token
from django.views.decorators.csrf import csrf_exempt

def generate_csv_report(data, filename, headers):
    """Generate CSV report from data"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(data)
    
    return response

def generate_pdf_report(data, filename, title, headers, summary_data=None):
    """Generate PDF report from data"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    
    # Create the PDF object
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Add title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))
    
    # Add summary if provided
    if summary_data:
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20
        )
        for key, value in summary_data.items():
            elements.append(Paragraph(f"<b>{key}:</b> {value}", summary_style))
        elements.append(Spacer(1, 20))
    
    # Create table
    if data:
        table = Table([headers] + data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
    
    # Build PDF
    doc.build(elements)
    return response

def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            return redirect('login')  # Redirect to login page after successful registration
    else:
        form = SignUpForm()
    
    return render(request, 'authentication/register.html', {'form': form})

# Register API
@csrf_exempt
@require_http_methods(["POST"])
def register_api(request):
    """API endpoint for user registration"""
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
            # Handle form data (your current approach)
            data = request.POST
        
        # Create form with data
        form = SignUpForm(data)
        
        if form.is_valid():
            user = form.save()
            
            # Return success response with user data (no tokens - user must login)
            return JsonResponse({
                'success': True,
                'message': 'Account created successfully. Please login to continue.',
            }, status=201)  # 201 for successful creation
        else:
            # Return validation errors
            return JsonResponse({
                'success': False,
                'message': 'Validation failed',
                'errors': form.errors
            }, status=400)
            
    except Exception as e:
        # Handle unexpected errors
        return JsonResponse({
            'success': False,
            'message': 'Server error occurred',
            'errors': {'server': [str(e)]}
        }, status=500)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')  # Redirect to dashboard or homepage
        else:
            # Form is invalid, re-render with errors
            return render(request, 'authentication/login.html', {'form': form})
    else:
        form = AuthenticationForm()
        return render(request, 'authentication/login.html', {'form': form})

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
        verification_result = verify_otp(user, otp_code, purpose='login', session_id=session_id)
        
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

def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

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
            posts = posts.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(user__username__icontains=search_query)
            )
        
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
            
            post_data = {
                'id': post.id,
                'title': post.title,
                'description': post.description,
                'price': float(post.price) if post.price else None,
                'category': post.category,
                'category_display': post.get_category_display(),
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
        for category in categories:
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'category_image': category.category_image.url if category.category_image else None
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
        logger = logging.getLogger(__name__)
        logger.error(f"Dashboard API error: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'message': 'Internal server error',
            'errors': {'server': ['An unexpected error occurred']}
        }, status=500)

# @csrf_exempt 
# @require_http_methods(['POST'])
# def bookmark_toggle_api(request, post_id):
#     """API endpoint to toggle bookmark status"""
#     try:
#         # Get user from token
#         user = get_token_user(request)
#         if not user:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Authentication required',
#                 'errors': {'auth': ['Please provide valid authentication credentials']}
#             }, status=401)
        
#         post = get_object_or_404(Post, id=post_id)
        
#         # Check if this post is already bookmarked by the user
#         existing_bookmark = Bookmark.objects.filter(user=user, post=post).first()
        
#         if existing_bookmark:
#             # If bookmark already existed, delete it (toggle off)
#             existing_bookmark.delete()
#             is_bookmarked = False
#             status_text = 'removed'
#         else:
#             # Create a new bookmark
#             Bookmark.objects.create(user=user, post=post)
#             is_bookmarked = True
#             status_text = 'added'
        
#         return JsonResponse({
#             'success': True,
#             'message': f'Bookmark {status_text} successfully',
#             'data': {
#                 'is_bookmarked': is_bookmarked,
#                 'status': status_text,
#                 'post_id': post_id
#             }
#         }, status=200)
        
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': 'Error toggling bookmark',
#             'errors': {'server': [str(e)]}
#         }, status=500)

# @csrf_exempt
# @require_http_methods(['POST'])
# def like_post_api(request, post_id):
#     """API endpoint to toggle like status"""
#     try:
#         # Get user from token
#         user = get_token_user(request)
#         if not user:
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Authentication required',
#                 'errors': {'auth': ['Please provide valid authentication credentials']}
#             }, status=401)
        
#         post = get_object_or_404(Post, id=post_id)
        
#         if user in post.likes.all():
#             post.likes.remove(user)
#             liked = False
#             status_text = 'removed'
#         else:
#             post.likes.add(user)
#             liked = True
#             status_text = 'added'
        
#         return JsonResponse({
#             'success': True,
#             'message': f'Like {status_text} successfully',
#             'data': {
#                 'liked': liked,
#                 'total_likes': post.total_likes(),
#                 'status': status_text,
#                 'post_id': post_id
#             }
#         }, status=200)
        
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': 'Error toggling like',
#             'errors': {'server': [str(e)]}
#         }, status=500)

# @csrf_exempt
# @require_http_methods(['GET'])
# def categories_api(request):
    """API endpoint to get all available categories"""
    try:
        categories_data = []
        for choice in Post.CATEGORY_CHOICES:
            # Get count of products in each category
            count = Post.objects.filter(category=choice[0], inventory__gt=0).count()
            categories_data.append({
                'value': choice[0],
                'label': choice[1],
                'product_count': count
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Categories retrieved successfully',
            'data': {
                'categories': categories_data,
                'total_categories': len(categories_data)
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving categories',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def dashboard(request):
    """Legacy HTML view - kept for backward compatibility"""
    # Get filter parameters from the request
    search_query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', 'newest')
    
    # Start with all products (no job posts anymore)
    posts = Post.objects.all()
    
    # Filter out sold-out products (inventory must be greater than 0)
    posts = posts.filter(inventory__gt=0)
    
    # Filter out the user's own products if they are a vendor
    if request.user.is_vendor_role:
        posts = posts.exclude(user=request.user)
    
    # Apply search filter if provided
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Apply category filter if provided
    if category:
        # Convert to lowercase to match the model's CATEGORY_CHOICES keys
        category = category.lower()
        posts = posts.filter(category=category)
    
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
        # Order by average rating (we'll implement this later)
        posts = posts.order_by('-created_at')
    else:  # newest (default)
        posts = posts.order_by('-created_at')
    
    # Get all categories for the filter dropdown
    categories = Post.CATEGORY_CHOICES
    
    # Get user's bookmarked posts for easier template rendering
    bookmarked_posts = [bookmark.post.id for bookmark in Bookmark.objects.filter(user=request.user)]
    
    # Get user's liked posts for easier template rendering
    liked_posts = [post.id for post in Post.objects.filter(likes=request.user)]
    
    # Pagination
    paginator = Paginator(posts, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'posts': page_obj,
        'search_query': search_query,
        'selected_category': category,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'categories': categories,
        'bookmarked_posts': bookmarked_posts,
        'liked_posts': liked_posts,
        'total_products': posts.count(),
    }
    
    return render(request, 'authentication/dashboard.html', context)

# @login_required
# def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()
    
    # Check if the user is the owner of the post
    is_owner = (post.user == request.user)
    
    # Get auxiliary images for the product
    auxiliary_images = ProductImage.objects.filter(product=post).order_by('display_order')
    
    # Allow repeat purchases - remove the restriction
    # has_purchased = Purchase.objects.filter(
    #     buyer=request.user, 
    #     product=post, 
    #     status__in=['completed', 'processing']
    # ).exists()
    has_purchased = False  # Always allow purchases
    
    # Get product reviews
    reviews = ProductReview.objects.filter(product=post).order_by('-created_at')
    
    # Check if current user has already reviewed this product
    user_review = None
    if request.user.is_authenticated:
        user_review = ProductReview.objects.filter(product=post, reviewer=request.user).first()
    
    context = {
        'post': post,
        'is_bookmarked': is_bookmarked,
        'has_purchased': has_purchased,
        'is_owner': is_owner,
        'auxiliary_images': auxiliary_images,
        'reviews': reviews,
        'user_review': user_review,
    }
    
    return render(request, 'authentication/post_detail.html', context)

# @login_required
# def purchase_product(request, post_id):
#     if request.method == 'POST':
#         product = get_object_or_404(Post, id=post_id)
        
#         # Check if user is trying to buy their own product
#         if product.user == request.user:
#             messages.error(request, "You cannot purchase your own product.")
#             return redirect('post_detail', post_id=post_id)
        
#         # Check if price is None or not set
#         if product.price is None:
#             messages.error(request, f'Unable to purchase {product.title}. The product does not have a valid price.')
#             return redirect('post_detail', post_id=post_id)
        

#         # Check if product is out of stock
#         if product.inventory <= 0:
#             messages.error(request, f'Sorry, {product.title} is currently out of stock.')
#             return redirect('post_detail', post_id=post_id)
        
#         # Get quantity from form
#         try:
#             quantity = int(request.POST.get('quantity', 1))
#             if quantity <= 0:
#                 raise ValueError("Quantity must be positive")
#         except (ValueError, TypeError):
#             messages.error(request, "Please enter a valid quantity.")
#             return redirect('post_detail', post_id=post_id)
        
#         # Check if enough inventory (with fresh data to prevent race conditions)
#         product.refresh_from_db()  # Get latest inventory data
#         if product.inventory < quantity:
#             if product.inventory == 0:
#                 messages.error(request, f'Sorry, {product.title} is now out of stock.')
#             else:
#                 messages.error(request, f'Sorry, there are only {product.inventory} items available.')
#             return redirect('post_detail', post_id=post_id)
        
#         # Get delivery method and details
#         delivery_method = request.POST.get('delivery_method', 'pickup')
#         delivery_address = request.POST.get('delivery_address', '')
#         delivery_latitude = request.POST.get('delivery_latitude')
#         delivery_longitude = request.POST.get('delivery_longitude')
#         payment_method = request.POST.get('payment_method', 'momo')  # New payment method field
        
#         # Calculate total price
#         total_price = product.price * quantity
#         delivery_fee = Decimal('5.00') if delivery_method == 'delivery' else Decimal('0.00')
        
#         # Validate delivery details if delivery is selected
#         if delivery_method == 'delivery':
#             if not delivery_address:
#                 messages.error(request, "Please provide a delivery address for home delivery.")
#                 return redirect('post_detail', post_id=post_id)
        
#         # Determine initial status based on delivery method
#         initial_status = 'awaiting_delivery' if delivery_method == 'delivery' else 'awaiting_pickup'
        
#         # Create a new purchase with agaseke workflow
#         purchase = Purchase(
#             buyer=request.user,
#             product=product,
#             quantity=quantity,
#             purchase_price=total_price,
#             delivery_method=delivery_method,
#             payment_method=payment_method,
#             delivery_fee=delivery_fee,
#             delivery_address=delivery_address,
#             status=initial_status
#         )
        
#         # Add location coordinates if provided
#         if delivery_latitude and delivery_longitude:
#             try:
#                 purchase.delivery_latitude = float(delivery_latitude)
#                 purchase.delivery_longitude = float(delivery_longitude)
#             except (ValueError, TypeError):
#                 pass  # Ignore invalid coordinates
        
#         purchase.save()
        
#         # Update inventory immediately after successful purchase
#         product.inventory -= quantity
        
#         # Update statistics
#         product.total_purchases += 1
#         product.save()
        
#         # Update QR code to include this purchase
#         from .qr_utils import update_user_qr_code
#         update_user_qr_code(request.user)
        
#         # Success message based on delivery method
#         if delivery_method == 'delivery':
#             messages.success(request, f'You have successfully purchased {quantity} {product.title}! Total: RWF {total_price + delivery_fee:,.2f} (including RWF {delivery_fee:,.2f} delivery fee). agaseke will deliver to your address.')
#         else:
#             messages.success(request, f'You have successfully purchased {quantity} {product.title}! Please go to agaseke to collect your items.')
        
#         return redirect('purchase_history')
    
#     return redirect('post_detail', post_id=post_id)

# @login_required
# def bookmark_toggle(request, post_id):
#     if request.method == 'POST':
#         try:
#             post = get_object_or_404(Post, id=post_id)
            
#             # Check if this post is already bookmarked by the user
#             existing_bookmark = Bookmark.objects.filter(user=request.user, post=post).first()
            
#             if existing_bookmark:
#                 # If bookmark already existed, delete it (toggle off)
#                 existing_bookmark.delete()
#                 is_bookmarked = False
#                 status = 'removed'
#             else:
#                 # Create a new bookmark
#                 Bookmark.objects.create(user=request.user, post=post)
#                 is_bookmarked = True
#                 status = 'added'
            
#             return JsonResponse({
#                 'success': True,
#                 'is_bookmarked': is_bookmarked,
#                 'status': status,
#                 'post_id': post_id
#             })
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             }, status=500)
    
#     return JsonResponse({'error': 'Invalid request'}, status=400)

# @login_required
# def purchase_history(request):
#     purchases = Purchase.objects.filter(buyer=request.user).order_by('-created_at')
    
#     # Check if export is requested
#     export_format = request.GET.get('export')
#     if export_format in ['csv', 'pdf']:
#         # Prepare data for export
#         headers = ['Order ID', 'Product', 'Seller', 'Date', 'Price', 'Status', 'Quantity', 'Delivery Method']
#         data = []
        
#         for purchase in purchases:
#             data.append([
#                 purchase.order_id,
#                 purchase.product.title,
#                 f"{purchase.product.user.first_name} {purchase.product.user.last_name}",
#                 purchase.created_at.strftime('%Y-%m-%d %H:%M'),
#                 f"RWF {purchase.purchase_price:,.1f}",
#                 purchase.status.title(),
#                 purchase.quantity,
#                 purchase.delivery_method.title()
#             ])
        
#         # Summary data for PDF
#         summary_data = {
#             'Total Purchases': purchases.count(),
#             'Total Spent': f"RWF {(purchases.aggregate(total=Sum('purchase_price'))['total'] or 0):,.1f}",
#             'Completed Orders': purchases.filter(status='completed').count(),
#             'Pending Orders': purchases.filter(status__in=['pending', 'processing']).count(),
#             'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         }
        
#         filename = f"purchase_history_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#         title = f"Purchase History Report - {request.user.get_full_name() or request.user.username}"
        
#         if export_format == 'csv':
#             return generate_csv_report(data, filename, headers)
#         elif export_format == 'pdf':
#             return generate_pdf_report(data, filename, title, headers, summary_data)
    
#     context = {
#         'purchases': purchases
#     }
    
#     return render(request, 'authentication/purchase_history.html', context)

# @login_required
# def bookmarks(request):
#     bookmarks = Bookmark.objects.filter(user=request.user).order_by('-created_at')
    
#     context = {
#         'bookmarks': bookmarks
#     }
    
#     return render(request, 'authentication/bookmarks.html', context)

# @login_required
# def vendor_dashboard(request):
#     # Ensure user is a vendor
#     if not request.user.is_vendor_role:
#         messages.error(request, 'You need to be registered as a vendor to access this dashboard.')
#         return redirect('dashboard')
    
#     # Get vendor's products
#     products = Post.objects.filter(user=request.user)
    
#     # Get purchases for vendor's products
#     purchases = Purchase.objects.filter(product__user=request.user)
    
#     # Calculate statistics
#     total_sales = purchases.filter(status='completed').count()
#     total_revenue = request.user.total_sales
    
#     # Get recent purchases
#     recent_purchases = purchases.order_by('-created_at')[:5]
    
#     context = {
#         'products': products,
#         'purchases': purchases,
#         'total_sales': total_sales,
#         'total_revenue': total_revenue,
#         'recent_purchases': recent_purchases
#     }
    
#     return render(request, 'authentication/vendor_dashboard.html', context)

# @login_required
# def user_settings(request):
#     # Handle form submissions for profile/account updates and role upgrades
#     if request.method == 'POST':
#         form_type = request.POST.get('form_type')
#         upgrade_type = request.POST.get('upgrade_type')
        
#         # Profile picture upload (AJAX request)
#         if form_type == 'profile_picture':
#             if 'profile_picture' in request.FILES:
#                 try:
#                     user = request.user
#                     user.profile_picture = request.FILES['profile_picture']
#                     user.save()
                    
#                     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                         return JsonResponse({'success': True, 'message': 'Profile picture updated successfully!'})
#                     else:
#                         messages.success(request, 'Profile picture updated successfully!')
#                         return redirect('user_settings')
#                 except Exception as e:
#                     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                         return JsonResponse({'success': False, 'error': f'Failed to update profile picture: {str(e)}'})
#                     else:
#                         messages.error(request, f'Failed to update profile picture: {str(e)}')
#             else:
#                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                     return JsonResponse({'success': False, 'error': 'No image file provided'})
#                 else:
#                     messages.error(request, 'No image file provided')
        
#         # Profile form submission
#         elif form_type == 'profile':
#             first_name = request.POST.get('first_name')
#             last_name = request.POST.get('last_name')
#             email = request.POST.get('email')
#             phone_number = request.POST.get('phone_number')
            
#             # Update user profile
#             request.user.first_name = first_name
#             request.user.last_name = last_name
#             request.user.email = email
#             request.user.phone_number = phone_number
            
#             # Handle profile picture upload if included in the form
#             profile_picture = request.FILES.get('profile_picture')
#             if profile_picture:
#                 request.user.profile_picture = profile_picture
            
#             request.user.save()
#             messages.success(request, 'Profile updated successfully.')
#             return redirect('user_settings')
        
#         # Account form submission (password change)
#         elif form_type == 'account':
#             new_password = request.POST.get('new_password')
#             confirm_password = request.POST.get('confirm_password')
            
#             if new_password and confirm_password:
#                 if new_password == confirm_password:
#                     request.user.set_password(new_password)
#                     request.user.save()
#                     messages.success(request, 'Password changed successfully. Please log in again.')
#                     return redirect('login')
#                 else:
#                     messages.error(request, 'Passwords do not match.')
#             else:
#                 messages.error(request, 'Please fill in both password fields.')
        
#         # Role upgrade form submissions
#         elif upgrade_type == 'vendor':
#             # Process vendor upgrade
#             if request.user.is_vendor_role:
#                 messages.info(request, 'You are already registered as a vendor.')
#             else:
#                 # Enable vendor role without changing other roles
#                 request.user.is_vendor_role = True
#                 request.user.save()
#                 messages.success(request, 'Congratulations! Your account has been upgraded to include Vendor capabilities. You can now create product posts.')
    
#     return render(request, 'authentication/settings.html')

# @login_required
# def create_post(request):
#     # Check if user has vendor permissions
#     if not request.user.is_vendor_role:
#         messages.error(request, 'You need to upgrade your account to Vendor status to create product listings.')
#         return redirect('user_settings')
    
#     # Direct to product creation since we only have products now
#     return redirect('create_product')

# @login_required
# def create_product(request):
#     # Check if user has vendor role
#     if not request.user.is_vendor_role:
#         messages.error(request, 'You need to upgrade your account to Vendor status to create product listings.')
#         return redirect('user_settings')
    
#     if request.method == 'POST':
#         title = request.POST.get('title')
#         description = request.POST.get('description')
#         main_image = request.FILES.get('main_image')
#         price = request.POST.get('price')
#         category = request.POST.get('category')
#         inventory = request.POST.get('inventory', 1)
        
#         try:
#             inventory = int(inventory)
#             if inventory < 0:
#                 inventory = 1
#         except (ValueError, TypeError):
#             inventory = 1
        
#         if title and description and main_image and price:
#             # Create the main product (no post_type needed since all posts are products now)
#             post = Post(
#                 title=title,
#                 description=description,
#                 image=main_image,
#                 user=request.user,
#                 price=price,
#                 category=category,
#                 inventory=inventory
#             )
#             post.save()
            
#             # Process auxiliary images (limit to 5)
#             auxiliary_images = request.FILES.getlist('auxiliary_images')
#             print(f"DEBUG: Found {len(auxiliary_images)} auxiliary images in create_product")
#             max_images = min(len(auxiliary_images), 5)  # Limit to 5 images
            
#             for i in range(max_images):
#                 print(f"DEBUG: Creating auxiliary image {i+1} of {max_images}")
#                 ProductImage.objects.create(
#                     product=post,
#                     image=auxiliary_images[i],
#                     display_order=i
#                 )
                
#             messages.success(request, 'Product listing created successfully!')
#             return redirect('dashboard')
#         else:
#             messages.error(request, 'Please fill all required fields')
    
#     return render(request, 'authentication/create_product.html')

# @login_required
# def like_post(request, post_id):
#     if request.method == 'POST':
#         try:
#             post = get_object_or_404(Post, id=post_id)
            
#             if request.user in post.likes.all():
#                 post.likes.remove(request.user)
#                 liked = False
#             else:
#                 post.likes.add(request.user)
#                 liked = True
                
#             return JsonResponse({
#                 'liked': liked,
#                 'total_likes': post.total_likes()
#             })
#         except Exception as e:
#             return JsonResponse({
#                 'error': str(e)
#             }, status=500)
    
#     return JsonResponse({'error': 'Invalid request'}, status=400)

# Below functions are kept for backward compatibility but redirect to settings page
# @login_required
# def become_vendor(request):
#     if request.method == 'POST':
#         if request.user.is_vendor_role:
#             messages.info(request, 'You are already registered as a vendor.')
#         else:
#             request.user.is_vendor_role = True
#             request.user.save()
#             messages.success(request, 'Congratulations! Your account has been upgraded to Vendor status. You can now create product posts.')
    
#     return redirect('user_settings')

# @login_required
# def edit_product(request, product_id):
#     # Check if user has vendor role
#     if not request.user.is_vendor_role:
#         messages.error(request, 'You need to have Vendor status to edit product listings.')
#         return redirect('dashboard')
    
#     # Get the product (ensure it belongs to the user)
#     product = get_object_or_404(Post, id=product_id, user=request.user)
    
#     # Business Rule: Check if product has been purchased or bookmarked
#     has_purchases = Purchase.objects.filter(product=product).exists()
#     has_bookmarks = Bookmark.objects.filter(post=product).exists()
    
#     if has_purchases or has_bookmarks:
#         messages.error(request, 'This product cannot be edited as it has been purchased or bookmarked by customers.')
#         return redirect('vendor_dashboard')
    
#     # Get existing auxiliary images
#     auxiliary_images = ProductImage.objects.filter(product=product).order_by('display_order')
    
#     if request.method == 'POST':
#         title = request.POST.get('title')
#         description = request.POST.get('description')
#         price = request.POST.get('price')
#         category = request.POST.get('category')
#         inventory = request.POST.get('inventory')
        
#         if title and description and price:
#             # Update product details
#             product.title = title
#             product.description = description
#             product.price = price
#             product.category = category
            
#             # Update inventory if provided
#             if inventory:
#                 try:
#                     inventory_value = int(inventory)
#                     if inventory_value >= 0:
#                         product.inventory = inventory_value
#                 except (ValueError, TypeError):
#                     pass  # Keep existing inventory if invalid value
            
#             # Handle main image update if provided
#             main_image = request.FILES.get('main_image')
#             if main_image:
#                 product.image = main_image
            
#             product.save()
            
#             # Handle auxiliary images
#             # Check if any auxiliary images should be deleted
#             images_to_keep = request.POST.getlist('keep_auxiliary_image')
            
#             # Delete images not in the keep list
#             for aux_image in auxiliary_images:
#                 if str(aux_image.id) not in images_to_keep:
#                     aux_image.delete()
            
#             # Count remaining images after deletion
#             remaining_images_count = ProductImage.objects.filter(product=product).count()
            
#             # Calculate how many new images we can add
#             max_new_images = 5 - remaining_images_count
            
#             if max_new_images > 0:
#                 # Add new auxiliary images up to the allowed limit
#                 new_auxiliary_images = request.FILES.getlist('auxiliary_images')
#                 print(f"DEBUG: Found {len(new_auxiliary_images)} new auxiliary images")
#                 max_to_add = min(len(new_auxiliary_images), max_new_images)
                
#                 for i in range(max_to_add):
#                     print(f"DEBUG: Creating auxiliary image {i+1} of {max_to_add}")
#                     ProductImage.objects.create(
#                         product=product,
#                         image=new_auxiliary_images[i],
#                         display_order=remaining_images_count + i
#                     )
            
#             messages.success(request, 'Product updated successfully!')
#             return redirect('vendor_dashboard')
#         else:
#             messages.error(request, 'Please fill all required fields')
    
#     context = {
#         'product': product,
#         'auxiliary_images': auxiliary_images
#     }
    
#     return render(request, 'authentication/edit_product.html', context)

# agaseke Views
@login_required
@ensure_csrf_cookie
def user_qr_code(request):
    """Display user's QR code with their purchase information"""
    # Update/create QR code for the user
    user_qr = update_user_qr_code(request.user)
    
    # Get user's pending purchases (both pickup and delivery)
    pending_purchases = Purchase.objects.filter(
        buyer=request.user,
        status__in=['awaiting_pickup', 'awaiting_delivery']
    ).select_related('product')
    
    context = {
        'user_qr': user_qr,
        'pending_purchases': pending_purchases,
        'qr_expires_at': user_qr.expires_at,
    }
    
    return render(request, 'authentication/user_qr_code.html', context)

@login_required
def agaseke_dashboard(request):
    """Legacy HTML view - kept for backward compatibility"""
    if not request.user.is_agaseke():
        messages.error(request, 'Access denied. agaseke role required.')
        return redirect('dashboard')
    
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
        agaseke_user=request.user
    ).select_related('buyer', 'product')
    
    # Calculate revenue statistics
    total_commission = completed_purchases.aggregate(
        total=Sum('agaseke_commission_amount')
    )['total'] or 0
    
    monthly_commission = completed_purchases.filter(
        pickup_confirmed_at__month=timezone.now().month,
        pickup_confirmed_at__year=timezone.now().year
    ).aggregate(total=Sum('agaseke_commission_amount'))['total'] or 0
    
    context = {
        'awaiting_purchases': awaiting_purchases,
        'awaiting_deliveries': awaiting_deliveries,
        'out_for_delivery': out_for_delivery,
        'completed_purchases': completed_purchases[:10],  # Latest 10
        'total_commission': total_commission,
        'monthly_commission': monthly_commission,
        'total_completed': completed_purchases.count(),
    }
    
    return render(request, 'authentication/agaseke_dashboard.html', context)


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

@login_required
def scan_qr_code(request):
    """QR code scanner interface for agaseke users"""
    try:
        if not request.user.is_agaseke():
            messages.error(request, 'Access denied. agaseke role required.')
            return redirect('dashboard')
        
        # Create context for rendering
        context = {
            'page_title': 'QR Code Scanner',
            'error_message': None,
            'success_message': None,
        }
        
        if request.method == 'POST':
            qr_data = request.POST.get('qr_data')
            purchase_id = request.POST.get('purchase_id')
            
            if not qr_data:
                context['error_message'] = 'No QR data provided'
                messages.error(request, context['error_message'])
                return render(request, 'authentication/scan_qr_code.html', context)
            
            try:
                # Decode QR data
                decoded_data = decode_qr_data(qr_data.strip())
                
                if isinstance(decoded_data, dict) and 'error' in decoded_data:
                    context['error_message'] = decoded_data['error']
                    messages.error(request, decoded_data['error'])
                    return render(request, 'authentication/scan_qr_code.html', context)
                
                # Get purchase information
                purchase_info = get_user_purchases_from_qr(decoded_data)
                
                # If no purchases found or empty QR data
                if not purchase_info.get('purchases'):
                    context['error_message'] = 'No pending purchases found in this QR code.'
                    messages.warning(request, context['error_message'])
                    return render(request, 'authentication/scan_qr_code.html', context)
                
                # If purchase_id is provided, complete that specific purchase
                if purchase_id:
                    try:
                        # Find the specific purchase from the database
                        purchase = Purchase.objects.get(id=purchase_id)
                        
                        # Verify the purchase belongs to the user in the QR code
                        if purchase.buyer.id != purchase_info['user_id']:
                            context['error_message'] = 'Purchase verification failed: User mismatch.'
                            messages.error(request, context['error_message'])
                            return render(request, 'authentication/scan_qr_code.html', context)
                        
                        # Complete the purchase directly (fallback from JS flow)
                        purchase.status = 'completed'
                        purchase.agaseke_user = request.user
                        purchase.pickup_confirmed_at = timezone.now()
                        purchase.save()
                        
                        # Update vendor and buyer stats
                        vendor = purchase.product.user
                        vendor.total_sales += purchase.vendor_payment_amount
                        vendor.save()
                        
                        buyer = purchase.buyer
                        buyer.total_purchases += (purchase.purchase_price * purchase.quantity)
                        buyer.save()
                        
                        # Success message
                        context['success_message'] = f'Purchase {purchase.order_id} confirmed successfully! Vendor payment: RWF{purchase.vendor_payment_amount}, agaseke commission: RWF{purchase.agaseke_commission_amount}'
                        messages.success(request, context['success_message'])
                        
                        # Redirect to dashboard after successful completion
                        return redirect('agaseke_dashboard')
                    except Purchase.DoesNotExist:
                        context['error_message'] = f'Purchase not found with ID: {purchase_id}'
                        messages.error(request, context['error_message'])
                        return render(request, 'authentication/scan_qr_code.html', context)
                    except Exception as e:
                        context['error_message'] = f'Error processing purchase: {str(e)}'
                        messages.error(request, context['error_message'])
                        return render(request, 'authentication/scan_qr_code.html', context)
                
                # If no specific purchase_id, show all purchases
                user = get_object_or_404(User, id=purchase_info['user_id'])
                
                # Add data to context
                context.update({
                    'qr_data': purchase_info,
                    'user_info': user,
                    'success_message': f'Successfully retrieved purchase information for {user.username}.'
                })
                
                messages.success(request, context['success_message'])
                return render(request, 'authentication/scan_qr_code.html', context)
                
            except IOError as e:
                error_msg = f"QR code processing error: {str(e)}"
                context['error_message'] = error_msg
                messages.error(request, error_msg)
                return render(request, 'authentication/scan_qr_code.html', context)
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                context['error_message'] = error_msg
                messages.error(request, error_msg)
                return render(request, 'authentication/scan_qr_code.html', context)
        
        # For GET requests, just render the scan page
        return render(request, 'authentication/scan_qr_code.html', context)
        
    except Exception as e:
        messages.error(request, f"System error: {str(e)}")
        return redirect('agaseke_dashboard')

@login_required
def confirm_purchase_pickup(request, purchase_id):
    """Confirm purchase pickup and initiate OTP verification"""
    if not request.user.is_agaseke():
        messages.error(request, 'Access denied. agaseke role required.')
        return redirect('dashboard')
    
    purchase = get_object_or_404(Purchase, id=purchase_id, status='awaiting_pickup')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'request_otp':
            # Create OTP for buyer
            otp_result = create_otp(purchase.buyer, 'purchase_confirmation')
            
            return JsonResponse({
                'success': True,
                'message': f'OTP sent to {purchase.buyer.email}',
                'otp_id': otp_result['otp_id']
            })
        
        elif action == 'verify_otp':
            password = request.POST.get('password')
            otp_code = request.POST.get('otp_code')
            
            # Verify buyer's password
            if not purchase.buyer.check_password(password):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid password'
                })
            
            # Verify OTP
            otp_result = verify_otp(purchase.buyer, otp_code, 'purchase_confirmation')
            
            if not otp_result['valid']:
                return JsonResponse({
                    'success': False,
                    'error': otp_result['error']
                })
            
            # Complete the purchase
            purchase.status = 'completed'
            purchase.agaseke_user = request.user
            purchase.pickup_confirmed_at = timezone.now()
            purchase.save()
            
            # Update vendor and buyer stats
            vendor = purchase.product.user
            vendor.total_sales += purchase.vendor_payment_amount
            vendor.save()
            
            buyer = purchase.buyer
            buyer.total_purchases += (purchase.purchase_price * purchase.quantity)
            buyer.save()
            
            # Update product sales count only (inventory was already decremented during purchase)
            product = purchase.product
            product.total_purchases += purchase.quantity
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Purchase confirmed successfully!',
                'vendor_payment': str(purchase.vendor_payment_amount),
                'agaseke_commission': str(purchase.agaseke_commission_amount)
            })
    
    context = {
        'purchase': purchase,
        'payment_split': purchase.calculate_payment_split()
    }
    
    return render(request, 'authentication/confirm_purchase_pickup.html', context)

@login_required
def confirm_delivery(request, purchase_id):
    """Confirm delivery completion and initiate OTP verification"""
    if not request.user.is_agaseke():
        messages.error(request, 'Access denied. agaseke role required.')
        return redirect('dashboard')
    
    purchase = get_object_or_404(Purchase, id=purchase_id, status__in=['awaiting_delivery', 'out_for_delivery'])
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'mark_out_for_delivery':
            # Mark as out for delivery
            purchase.status = 'out_for_delivery'
            purchase.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Order marked as out for delivery!'
            })
        
        elif action == 'request_otp':
            # Create OTP for buyer
            otp_result = create_otp(purchase.buyer, 'delivery_confirmation')
            
            return JsonResponse({
                'success': True,
                'message': f'OTP sent to {purchase.buyer.email}',
                'otp_id': otp_result['otp_id']
            })
        
        elif action == 'verify_delivery':
            password = request.POST.get('password')
            otp_code = request.POST.get('otp_code')
            
            # Verify buyer's password
            if not purchase.buyer.check_password(password):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid password'
                })
            
            # Verify OTP
            otp_result = verify_otp(purchase.buyer, otp_code, 'delivery_confirmation')
            
            if not otp_result['valid']:
                return JsonResponse({
                    'success': False,
                    'error': otp_result['error']
                })
            
            # Complete the delivery
            purchase.status = 'completed'
            purchase.agaseke_user = request.user
            purchase.pickup_confirmed_at = timezone.now()  # Using same field for delivery confirmation time
            purchase.save()
            
            # Update vendor and buyer stats
            vendor = purchase.product.user
            vendor.total_sales += purchase.vendor_payment_amount
            vendor.save()
            
            buyer = purchase.buyer
            buyer.total_purchases += purchase.purchase_price
            buyer.save()
            
            # Update product sales count only (inventory was already decremented during purchase)
            product = purchase.product
            product.total_purchases += purchase.quantity
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Delivery confirmed successfully!',
                'vendor_payment': str(purchase.vendor_payment_amount),
                'agaseke_commission': str(purchase.agaseke_commission_amount)
            })
    
    context = {
        'purchase': purchase,
        'payment_split': purchase.calculate_payment_split(),
        'is_delivery': True
    }
    
    return render(request, 'authentication/confirm_purchase_pickup.html', context)

@login_required
@ensure_csrf_cookie
@require_http_methods(["POST"])
def update_qr_code_ajax(request):
    """AJAX endpoint to update user's QR code"""
    print(f"Update QR request received:")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    print(f"CSRF Token in POST: {request.POST.get('csrfmiddlewaretoken', 'Not found')}")
    print(f"CSRF Token in META: {request.META.get('HTTP_X_CSRFTOKEN', 'Not found')}")
    
    if request.method == 'POST':
        user_qr = update_user_qr_code(request.user)
        
        return JsonResponse({
            'success': True,
            'qr_image_url': user_qr.qr_image.url if user_qr.qr_image else None,
            'expires_at': user_qr.expires_at.isoformat()
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# @login_required
# def agaseke_purchase_history(request):
#     """View purchase history for agaseke users"""
#     if not request.user.is_agaseke():
#         messages.error(request, 'Access denied. agaseke role required.')
#         return redirect('dashboard')
    
#     purchases = Purchase.objects.filter(
#         agaseke_user=request.user,
#         status='completed'
#     ).select_related('buyer', 'product', 'product__user').order_by('-pickup_confirmed_at')
    
#     # Pagination could be added here
#     context = {
#         'purchases': purchases,
#         'total_commission': purchases.aggregate(
#             total=Sum('agaseke_commission_amount')
#         )['total'] or 0
#     }
    
#     return render(request, 'authentication/agaseke_purchase_history.html', context)

# @login_required
# def sales_statistics(request):
#     """Sales statistics view showing detailed financial breakdown for vendors and agaseke agents"""
    
#     # Check if export is requested
#     export_format = request.GET.get('export')
    
#     if request.user.is_vendor_role:
#         # Vendor statistics - show their earnings (80% of product price)
#         purchases = Purchase.objects.filter(
#             product__user=request.user,
#             status='completed'
#         ).select_related('product', 'buyer')
        
#         # Calculate vendor statistics
#         total_sales = purchases.count()
#         total_revenue = purchases.aggregate(
#             total=Sum('vendor_payment_amount')
#         )['total'] or 0
        
#         # Monthly statistics
#         current_month = timezone.now().month
#         current_year = timezone.now().year
#         monthly_purchases = purchases.filter(
#             pickup_confirmed_at__month=current_month,
#             pickup_confirmed_at__year=current_year
#         )
#         monthly_revenue = monthly_purchases.aggregate(
#             total=Sum('vendor_payment_amount')
#         )['total'] or 0
        
#         # Product-wise breakdown
#         product_stats = purchases.values('product__title').annotate(
#             total_sales=Count('id'),
#             total_revenue=Sum('vendor_payment_amount'),
#             avg_price=Avg('vendor_payment_amount')
#         ).order_by('-total_revenue')
        
#         # Recent transactions
#         recent_transactions = purchases.order_by('-pickup_confirmed_at')[:10]
        
#         # Handle export for vendor
#         if export_format in ['csv', 'pdf']:
#             if export_format == 'csv':
#                 headers = ['Product', 'Total Sales', 'Total Revenue', 'Average Price']
#                 data = []
#                 for product in product_stats:
#                     data.append([
#                         product['product__title'],
#                         product['total_sales'],
#                         f"RWF {product['total_revenue']:,.1f}",
#                         f"RWF {product['avg_price']:,.1f}"
#                     ])
#                 filename = f"vendor_sales_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#                 return generate_csv_report(data, filename, headers)
#             elif export_format == 'pdf':
#                 headers = ['Product', 'Total Sales', 'Total Revenue', 'Average Price']
#                 data = []
#                 for product in product_stats:
#                     data.append([
#                         product['product__title'],
#                         product['total_sales'],
#                         f"RWF {product['total_revenue']:,.1f}",
#                         f"RWF {product['avg_price']:,.1f}"
#                     ])
#                 summary_data = {
#                     'Total Sales': total_sales,
#                     'Total Revenue': f"RWF {total_revenue:,.1f}",
#                     'Monthly Revenue': f"RWF {monthly_revenue:,.1f}",
#                     'Commission Rate': '80%',
#                     'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#                 }
#                 filename = f"vendor_sales_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#                 title = f"Vendor Sales Report - {request.user.get_full_name() or request.user.username}"
#                 return generate_pdf_report(data, filename, title, headers, summary_data)
        
#         context = {
#             'user_type': 'vendor',
#             'total_sales': total_sales,
#             'total_revenue': total_revenue,
#             'monthly_revenue': monthly_revenue,
#             'monthly_sales': monthly_purchases.count(),
#             'product_stats': product_stats,
#             'recent_transactions': recent_transactions,
#             'commission_rate': 80,  # Vendor gets 80%
#             'agaseke_rate': 20,   # agaseke gets 20%
#         }
        
#     elif request.user.is_agaseke():
#         # agaseke agent statistics - show their commission (20% of product price + delivery fees)
#         purchases = Purchase.objects.filter(
#             agaseke_user=request.user,
#             status='completed'
#         ).select_related('product', 'buyer', 'product__user')
        
#         # Calculate agaseke statistics
#         total_transactions = purchases.count()
#         total_commission = purchases.aggregate(
#             total=Sum('agaseke_commission_amount')
#         )['total'] or 0
        
#         # Monthly statistics
#         current_month = timezone.now().month
#         current_year = timezone.now().year
#         monthly_purchases = purchases.filter(
#             pickup_confirmed_at__month=current_month,
#             pickup_confirmed_at__year=current_year
#         )
#         monthly_commission = monthly_purchases.aggregate(
#             total=Sum('agaseke_commission_amount')
#         )['total'] or 0
        
#         # Breakdown by commission type
#         total_product_price = purchases.aggregate(total=Sum('purchase_price'))['total'] or 0
#         total_delivery_fees = purchases.aggregate(total=Sum('delivery_fee'))['total'] or 0
#         total_commission_amount = purchases.aggregate(total=Sum('agaseke_commission_amount'))['total'] or 0
        
#         commission_breakdown = {
#             'product_commission': total_product_price * Decimal('0.2'),
#             'delivery_fees': total_delivery_fees,
#             'total_commission': total_commission_amount
#         }
        
#         # Vendor-wise breakdown - get unique vendors with their stats
#         vendor_stats = []
        
#         # Use values() to get unique vendors with their aggregated stats
#         vendor_aggregates = purchases.values('product__user__id', 'product__user__username').annotate(
#             total_transactions=Count('id'),
#             total_commission=Sum('agaseke_commission_amount'),
#             avg_commission=Avg('agaseke_commission_amount')
#         ).order_by('-total_commission')
        
#         for vendor_data in vendor_aggregates:
#             vendor_stats.append({
#                 'vendor_id': vendor_data['product__user__id'],
#                 'vendor_username': vendor_data['product__user__username'],
#                 'total_transactions': vendor_data['total_transactions'],
#                 'total_commission': vendor_data['total_commission'] or 0,
#                 'avg_commission': vendor_data['avg_commission'] or 0
#             })
        

        
#         # Recent transactions
#         recent_transactions = purchases.order_by('-pickup_confirmed_at')[:10]
        
#         # Handle export for agaseke
#         if export_format in ['csv', 'pdf']:
#             if export_format == 'csv':
#                 headers = ['Vendor', 'Transactions', 'Total Commission', 'Average Commission']
#                 data = []
#                 for vendor in vendor_stats:
#                     data.append([
#                         vendor['vendor_username'],
#                         vendor['total_transactions'],
#                         f"RWF {vendor['total_commission']:,.1f}",
#                         f"RWF {vendor['avg_commission']:,.1f}"
#                     ])
#                 filename = f"agaseke_commission_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#                 return generate_csv_report(data, filename, headers)
#             elif export_format == 'pdf':
#                 headers = ['Vendor', 'Transactions', 'Total Commission', 'Average Commission']
#                 data = []
#                 for vendor in vendor_stats:
#                     data.append([
#                         vendor['vendor_username'],
#                         vendor['total_transactions'],
#                         f"RWF {vendor['total_commission']:,.1f}",
#                         f"RWF {vendor['avg_commission']:,.1f}"
#                     ])
#                 summary_data = {
#                     'Total Transactions': total_transactions,
#                     'Total Commission': f"RWF {total_commission:,.1f}",
#                     'Monthly Commission': f"RWF {monthly_commission:,.1f}",
#                     'Commission Rate': '20% + Delivery Fees',
#                     'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#                 }
#                 filename = f"agaseke_commission_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#                 title = f"agaseke Commission Report - {request.user.get_full_name() or request.user.username}"
#                 return generate_pdf_report(data, filename, title, headers, summary_data)
        
#         context = {
#             'user_type': 'agaseke',
#             'total_transactions': total_transactions,
#             'total_commission': total_commission,
#             'monthly_commission': monthly_commission,
#             'monthly_transactions': monthly_purchases.count(),
#             'commission_breakdown': commission_breakdown,
#             'vendor_stats': vendor_stats,
#             'recent_transactions': recent_transactions,
#             'commission_rate': 20,  # agaseke gets 20%
#             'vendor_rate': 80,      # Vendor gets 80%
#         }
        
#     else:
#         # Regular user - show their purchase history
#         purchases = Purchase.objects.filter(
#             buyer=request.user,
#             status='completed'
#         ).select_related('product', 'product__user')
        
#         total_spent = purchases.aggregate(
#             total=Sum('purchase_price')
#         )['total'] or 0
        
#         monthly_purchases = purchases.filter(
#             created_at__month=timezone.now().month,
#             created_at__year=timezone.now().year
#         )
#         monthly_spent = monthly_purchases.aggregate(
#             total=Sum('purchase_price')
#         )['total'] or 0
        
#         # Handle export for customer
#         if export_format in ['csv', 'pdf']:
#             headers = ['Product', 'Seller', 'Date', 'Price', 'Status']
#             data = []
#             for purchase in purchases:
#                 data.append([
#                     purchase.product.title,
#                     f"{purchase.product.user.first_name} {purchase.product.user.last_name}",
#                     purchase.created_at.strftime('%Y-%m-%d %H:%M'),
#                     f"RWF {purchase.purchase_price:,.1f}",
#                     purchase.status.title()
#                 ])
            
#             if export_format == 'csv':
#                 filename = f"customer_purchases_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#                 return generate_csv_report(data, filename, headers)
#             elif export_format == 'pdf':
#                 summary_data = {
#                     'Total Purchases': purchases.count(),
#                     'Total Spent': f"RWF {total_spent:,.1f}",
#                     'Monthly Spent': f"RWF {monthly_spent:,.1f}",
#                     'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#                 }
#                 filename = f"customer_purchases_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#                 title = f"Customer Purchase Report - {request.user.get_full_name() or request.user.username}"
#                 return generate_pdf_report(data, filename, title, headers, summary_data)
        
#         context = {
#             'user_type': 'customer',
#             'total_purchases': purchases.count(),
#             'total_spent': total_spent,
#             'monthly_spent': monthly_spent,
#             'monthly_purchases': monthly_purchases.count(),
#             'recent_transactions': purchases.order_by('-created_at')[:10],
#         }
    
#     return render(request, 'authentication/sales_statistics.html', context)

# @login_required
# def vendor_statistics_for_agaseke(request, vendor_id):
#     """agaseke users can view detailed statistics for a specific vendor"""
#     if not request.user.is_agaseke():
#         messages.error(request, 'Access denied. agaseke role required.')
#         return redirect('dashboard')
    
#     # Get the vendor
#     vendor = get_object_or_404(User, id=vendor_id, is_vendor_role=True)
    
#     # Get all purchases for this vendor
#     purchases = Purchase.objects.filter(
#         product__user=vendor,
#         status='completed'
#     ).select_related('product', 'buyer', 'agaseke_user')
    
#     # Calculate vendor statistics (as if agaseke is viewing the vendor's dashboard)
#     total_sales = purchases.count()
#     total_revenue = purchases.aggregate(
#         total=Sum('vendor_payment_amount')
#     )['total'] or 0
    
#     # Monthly statistics
#     current_month = timezone.now().month
#     current_year = timezone.now().year
#     monthly_purchases = purchases.filter(
#         pickup_confirmed_at__month=current_month,
#         pickup_confirmed_at__year=current_year
#     )
#     monthly_revenue = monthly_purchases.aggregate(
#         total=Sum('vendor_payment_amount')
#     )['total'] or 0
    
#     # Product-wise breakdown
#     product_stats = purchases.values('product__title').annotate(
#         total_sales=Count('id'),
#         total_revenue=Sum('vendor_payment_amount'),
#         avg_price=Avg('vendor_payment_amount')
#     ).order_by('-total_revenue')
    
#     # agaseke commission from this vendor
#     agaseke_commission = purchases.aggregate(
#         total=Sum('agaseke_commission_amount')
#     )['total'] or 0
    
#     # Monthly agaseke commission
#     monthly_agaseke_commission = monthly_purchases.aggregate(
#         total=Sum('agaseke_commission_amount')
#     )['total'] or 0
    
#     # Recent transactions
#     recent_transactions = purchases.order_by('-pickup_confirmed_at')[:10]
    
#     # Commission breakdown
#     total_product_price = purchases.aggregate(total=Sum('purchase_price'))['total'] or 0
#     total_delivery_fees = purchases.aggregate(total=Sum('delivery_fee'))['total'] or 0
    
#     commission_breakdown = {
#         'vendor_earnings': total_revenue,
#         'agaseke_commission': agaseke_commission,
#         'product_commission': total_product_price * Decimal('0.2'),
#         'delivery_fees': total_delivery_fees,
#         'total_transaction_value': total_product_price + total_delivery_fees
#     }
    
#     context = {
#         'vendor': vendor,
#         'total_sales': total_sales,
#         'total_revenue': total_revenue,
#         'monthly_revenue': monthly_revenue,
#         'monthly_sales': monthly_purchases.count(),
#         'product_stats': product_stats,
#         'recent_transactions': recent_transactions,
#         'agaseke_commission': agaseke_commission,
#         'monthly_agaseke_commission': monthly_agaseke_commission,
#         'commission_breakdown': commission_breakdown,
#         'commission_rate': 80,  # Vendor gets 80%
#         'agaseke_rate': 20,   # agaseke gets 20%
#     }
    
#     return render(request, 'authentication/vendor_statistics_for_agaseke.html', context)
