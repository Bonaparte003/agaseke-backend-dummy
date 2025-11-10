from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from posts.models import Post, Bookmark, ProductReview
from products.models import ProductImage
from authentication.utils import get_token_user
from authentication.decorators import jwt_required
from authentication.serializers_helpers import serialize_post, serialize_review, serialize_bookmark

@csrf_exempt 
@require_http_methods(['POST'])
def bookmark_toggle_api(request, post_id):
    """API endpoint to toggle bookmark status"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        post = get_object_or_404(Post, id=post_id)
        
        # Check if this post is already bookmarked by the user
        existing_bookmark = Bookmark.objects.filter(user=user, post=post).first()
        
        if existing_bookmark:
            # If bookmark already existed, delete it (toggle off)
            existing_bookmark.delete()
            is_bookmarked = False
            status_text = 'removed'
        else:
            # Create a new bookmark
            Bookmark.objects.create(user=user, post=post)
            is_bookmarked = True
            status_text = 'added'
        
        return JsonResponse({
            'success': True,
            'message': f'Bookmark {status_text} successfully',
            'data': {
                'is_bookmarked': is_bookmarked,
                'status': status_text,
                'post_id': post_id
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error toggling bookmark',
            'errors': {'server': [str(e)]}
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def like_post_api(request, post_id):
    """API endpoint to toggle like status"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        post = get_object_or_404(Post, id=post_id)
        
        if user in post.likes.all():
            post.likes.remove(user)
            liked = False
            status_text = 'removed'
        else:
            post.likes.add(user)
            liked = True
            status_text = 'added'
        
        return JsonResponse({
            'success': True,
            'message': f'Like {status_text} successfully',
            'data': {
                'liked': liked,
                'total_likes': post.total_likes(),
                'status': status_text,
                'post_id': post_id
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error toggling like',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def post_detail(request, post_id):
    """Legacy HTML view - kept for backward compatibility"""
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


@csrf_exempt
@require_http_methods(['GET'])
def post_detail_api(request, post_id):
    """API endpoint to get post/product details"""
    try:
        # Get user from token (optional for viewing)
        user = get_token_user(request)
        
        post = get_object_or_404(Post, id=post_id)
        
        # Get product reviews
        reviews = ProductReview.objects.filter(product=post).order_by('-created_at')
        reviews_data = [serialize_review(review) for review in reviews]
        
        # Check if current user has already reviewed this product
        user_review = None
        if user:
            user_review_obj = ProductReview.objects.filter(product=post, reviewer=user).first()
            if user_review_obj:
                user_review = serialize_review(user_review_obj)
        
        # Serialize post
        post_data = serialize_post(post, user)
        post_data['is_owner'] = (user and post.user == user)
        
        # Check if user has purchased (for review eligibility)
        has_purchased = False
        if user:
            from products.models import Purchase
            has_purchased = Purchase.objects.filter(
                buyer=user,
                product=post,
                status='completed'
            ).exists()
        
        post_data['has_purchased'] = has_purchased
        post_data['reviews'] = reviews_data
        post_data['user_review'] = user_review
        
        return JsonResponse({
            'success': True,
            'message': 'Post details retrieved successfully',
            'data': post_data
        }, status=200)
        
    except Post.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Post not found',
            'errors': {'post': ['Post with this ID does not exist']}
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving post details',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def bookmark_toggle(request, post_id):
    if request.method == 'POST':
        try:
            post = get_object_or_404(Post, id=post_id)
            
            # Check if this post is already bookmarked by the user
            existing_bookmark = Bookmark.objects.filter(user=request.user, post=post).first()
            
            if existing_bookmark:
                # If bookmark already existed, delete it (toggle off)
                existing_bookmark.delete()
                is_bookmarked = False
                status = 'removed'
            else:
                # Create a new bookmark
                Bookmark.objects.create(user=request.user, post=post)
                is_bookmarked = True
                status = 'added'
            
            return JsonResponse({
                'success': True,
                'is_bookmarked': is_bookmarked,
                'status': status,
                'post_id': post_id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def bookmarks(request):
    """Legacy HTML view - kept for backward compatibility"""
    bookmarks = Bookmark.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'bookmarks': bookmarks
    }
    
    return render(request, 'authentication/bookmarks.html', context)


@csrf_exempt
@require_http_methods(['GET'])
def bookmarks_api(request):
    """API endpoint to get user's bookmarks"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        bookmarks = Bookmark.objects.filter(user=user).order_by('-created_at')
        bookmarks_data = [serialize_bookmark(bookmark) for bookmark in bookmarks]
        
        return JsonResponse({
            'success': True,
            'message': 'Bookmarks retrieved successfully',
            'data': {
                'bookmarks': bookmarks_data,
                'total': len(bookmarks_data)
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving bookmarks',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def create_post(request):
    """Legacy HTML view - kept for backward compatibility"""
    # Check if user has vendor permissions
    if not request.user.is_vendor_role:
        messages.error(request, 'You need to upgrade your account to Vendor status to create product listings.')
        return redirect('user_settings')
    
    # Direct to product creation since we only have products now
    return redirect('create_product')

@login_required
def like_post(request, post_id):
    if request.method == 'POST':
        try:
            post = get_object_or_404(Post, id=post_id)
            
            if request.user in post.likes.all():
                post.likes.remove(request.user)
                liked = False
            else:
                post.likes.add(request.user)
                liked = True
                
            return JsonResponse({
                'liked': liked,
                'total_likes': post.total_likes()
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

