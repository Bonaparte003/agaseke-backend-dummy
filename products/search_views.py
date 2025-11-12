"""
Advanced search API views for products
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator

from posts.models import Post, Category
from authentication.utils import get_token_user
from authentication.serializers_helpers import serialize_post


@csrf_exempt
@require_http_methods(['GET'])
def search_products_api(request):
    """
    Advanced product search API with multi-word search and filtering
    
    Query Parameters:
    - q: Search query (supports multiple words)
    - category: Category filter (ID or slug)
    - min_price: Minimum price filter
    - max_price: Maximum price filter
    - sort: Sort order (relevance, newest, price_low, price_high, popular, rating)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    """
    try:
        # Get user from token (optional for search)
        user = get_token_user(request)
        
        # Get search parameters
        search_query = request.GET.get('q', '').strip()
        category = request.GET.get('category', '')
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')
        sort_by = request.GET.get('sort', 'relevance')
        page_number = request.GET.get('page', 1)
        page_size = int(request.GET.get('page_size', 20))
        
        # Validate page_size
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 20
        
        # Require search query
        if not search_query:
            return JsonResponse({
                'success': False,
                'message': 'Search query required',
                'errors': {'q': ['Please provide a search query']}
            }, status=400)
        
        # Start with all available products
        posts = Post.objects.filter(inventory__gt=0)
        
        # Exclude vendor's own products if logged in as vendor
        if user and user.is_vendor_role:
            posts = posts.exclude(user=user)
        
        # Apply multi-word search
        search_words = search_query.split()
        search_filter = Q()
        
        for word in search_words:
            word_filter = Q()
            word_filter |= Q(title__icontains=word)
            word_filter |= Q(description__icontains=word)
            word_filter |= Q(user__username__icontains=word)
            word_filter |= Q(user__first_name__icontains=word)
            word_filter |= Q(user__last_name__icontains=word)
            word_filter |= Q(category__name__icontains=word)
            search_filter &= word_filter
        
        posts = posts.filter(search_filter)
        
        # Apply category filter
        if category:
            try:
                category_id = int(category)
                posts = posts.filter(category__id=category_id, category__is_active=True)
            except (ValueError, TypeError):
                posts = posts.filter(category__slug=category, category__is_active=True)
        
        # Apply price filters
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
        
        # Get total count before pagination
        total_results = posts.count()
        
        # Apply sorting
        if sort_by == 'price_low':
            posts = posts.order_by('price', '-created_at')
        elif sort_by == 'price_high':
            posts = posts.order_by('-price', '-created_at')
        elif sort_by == 'popular':
            posts = posts.order_by('-total_purchases', '-created_at')
        elif sort_by == 'rating':
            posts = posts.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating', '-created_at')
        elif sort_by == 'newest':
            posts = posts.order_by('-created_at')
        else:  # relevance (default)
            # For relevance, prioritize title matches over description
            # This is a simple relevance - can be enhanced with full-text search
            posts = posts.order_by('-created_at')
        
        # Pagination
        paginator = Paginator(posts, page_size)
        try:
            page_obj = paginator.get_page(page_number)
        except Exception:
            page_obj = paginator.get_page(1)
        
        # Serialize results
        results = []
        for post in page_obj:
            post_data = serialize_post(post, user)
            
            # Add search relevance info
            post_data['search_relevance'] = {
                'title_match': any(word.lower() in post.title.lower() for word in search_words),
                'description_match': any(word.lower() in post.description.lower() for word in search_words),
                'vendor_match': any(word.lower() in post.user.username.lower() for word in search_words),
                'category_match': any(word.lower() in post.category.name.lower() for word in search_words) if post.category else False
            }
            
            results.append(post_data)
        
        # Get search suggestions (categories that match)
        category_suggestions = []
        if search_query:
            matching_categories = Category.objects.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query),
                is_active=True
            )[:5]
            
            for cat in matching_categories:
                category_suggestions.append({
                    'id': cat.id,
                    'name': cat.name,
                    'slug': cat.slug,
                    'product_count': cat.product_count()
                })
        
        return JsonResponse({
            'success': True,
            'message': f'Found {total_results} results for "{search_query}"',
            'data': {
                'query': search_query,
                'results': results,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'page_size': page_size,
                    'total_results': total_results,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                },
                'filters_applied': {
                    'category': category,
                    'min_price': min_price,
                    'max_price': max_price,
                    'sort_by': sort_by
                },
                'suggestions': {
                    'categories': category_suggestions
                }
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Search error',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['GET'])
def search_suggestions_api(request):
    """
    Get search suggestions/autocomplete
    
    Query Parameters:
    - q: Partial search query (minimum 2 characters)
    - limit: Number of suggestions (default: 10)
    """
    try:
        query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 10))
        
        if len(query) < 2:
            return JsonResponse({
                'success': False,
                'message': 'Query too short',
                'errors': {'q': ['Minimum 2 characters required']}
            }, status=400)
        
        # Limit suggestions
        if limit > 20:
            limit = 20
        
        suggestions = {
            'products': [],
            'categories': [],
            'vendors': []
        }
        
        # Product suggestions (title matches)
        products = Post.objects.filter(
            title__icontains=query,
            inventory__gt=0
        ).order_by('-total_purchases')[:limit]
        
        for product in products:
            suggestions['products'].append({
                'id': product.id,
                'title': product.title,
                'price': float(product.price),
                'image_url': product.image.url if product.image else None
            })
        
        # Category suggestions
        categories = Category.objects.filter(
            name__icontains=query,
            is_active=True
        ).order_by('display_order')[:5]
        
        for category in categories:
            suggestions['categories'].append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug
            })
        
        # Vendor suggestions
        from users.models import User
        vendors = User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query),
            is_vendor_role=True
        )[:5]
        
        for vendor in vendors:
            suggestions['vendors'].append({
                'id': vendor.id,
                'username': vendor.username,
                'full_name': f"{vendor.first_name} {vendor.last_name}".strip()
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Suggestions retrieved',
            'data': {
                'query': query,
                'suggestions': suggestions
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error getting suggestions',
            'errors': {'server': [str(e)]}
        }, status=500)

