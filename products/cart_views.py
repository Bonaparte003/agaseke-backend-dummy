"""
Cart API views for shopping cart functionality
"""
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404

from products.models import Cart, CartItem
from posts.models import Post
from authentication.utils import get_token_user
from authentication.serializers_helpers import serialize_post


@csrf_exempt
@require_http_methods(['GET'])
def view_cart_api(request):
    """API endpoint to view cart contents"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Get or create cart for user
        cart, created = Cart.objects.get_or_create(user=user)
        
        # Serialize cart items
        cart_items_data = []
        for item in cart.items.all().select_related('product', 'product__category', 'product__user'):
            # Check if product is still available
            is_available = item.product.inventory >= item.quantity
            is_sold_out = item.product.inventory == 0
            
            cart_items_data.append({
                'id': item.id,
                'product': {
                    'id': item.product.id,
                    'title': item.product.title,
                    'price': float(item.product.price),
                    'is_great_deal': item.product.is_great_deal,
                    'original_price': float(item.product.original_price) if item.product.original_price else None,
                    'discount_percentage': item.product.discount_percentage() if item.product.is_great_deal else None,
                    'image_url': item.product.image.url if item.product.image else None,
                    'inventory': item.product.inventory,
                    'category': {
                        'id': item.product.category.id,
                        'name': item.product.category.name,
                        'slug': item.product.category.slug
                    } if item.product.category else None,
                    'vendor': {
                        'id': item.product.user.id,
                        'username': item.product.user.username,
                        'is_vendor_role': item.product.user.is_vendor_role
                    }
                },
                'quantity': item.quantity,
                'subtotal': float(item.subtotal()),
                'is_available': is_available,
                'is_sold_out': is_sold_out,
                'added_at': item.added_at.isoformat(),
                'updated_at': item.updated_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Cart retrieved successfully',
            'data': {
                'cart_id': cart.id,
                'items': cart_items_data,
                'total_items': cart.total_items(),
                'total_price': float(cart.total_price()),
                'created_at': cart.created_at.isoformat(),
                'updated_at': cart.updated_at.isoformat()
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving cart',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def add_to_cart_api(request):
    """API endpoint to add item to cart"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Parse request data
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data',
                'errors': {'json': ['Request body contains invalid JSON']}
            }, status=400)
        
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        # Validate inputs
        if not product_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields',
                'errors': {'product_id': ['Product ID is required']}
            }, status=400)
        
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity',
                'errors': {'quantity': ['Quantity must be a positive integer']}
            }, status=400)
        
        # Get product
        product = get_object_or_404(Post, id=product_id)
        
        # Check if product has enough inventory
        if product.inventory < quantity:
            return JsonResponse({
                'success': False,
                'message': 'Insufficient inventory',
                'errors': {'inventory': [f'Only {product.inventory} items available']}
            }, status=400)
        
        # Check if product is sold out
        if product.inventory == 0:
            return JsonResponse({
                'success': False,
                'message': 'Product is sold out',
                'errors': {'inventory': ['This product is currently out of stock']}
            }, status=400)
        
        # Prevent user from adding their own products to cart (if they're a vendor)
        if user.is_vendor_role and product.user == user:
            return JsonResponse({
                'success': False,
                'message': 'Cannot add your own product to cart',
                'errors': {'product': ['You cannot purchase your own products']}
            }, status=400)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=user)
        
        # Check if item already exists in cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            # Item already in cart, update quantity
            new_quantity = cart_item.quantity + quantity
            
            # Check if new quantity exceeds inventory
            if new_quantity > product.inventory:
                return JsonResponse({
                    'success': False,
                    'message': 'Insufficient inventory',
                    'errors': {'inventory': [f'Cannot add {quantity} more. Only {product.inventory - cart_item.quantity} items available']}
                }, status=400)
            
            cart_item.quantity = new_quantity
            cart_item.save()
            action = 'updated'
        else:
            action = 'added'
        
        return JsonResponse({
            'success': True,
            'message': f'Item {action} to cart successfully',
            'data': {
                'cart_item_id': cart_item.id,
                'product_id': product.id,
                'product_title': product.title,
                'quantity': cart_item.quantity,
                'subtotal': float(cart_item.subtotal()),
                'total_items': cart.total_items(),
                'total_price': float(cart.total_price()),
                'action': action
            }
        }, status=201 if item_created else 200)
        
    except Post.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found',
            'errors': {'product': ['Product with this ID does not exist']}
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error adding item to cart',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['PUT', 'PATCH'])
def update_cart_item_api(request, item_id):
    """API endpoint to update cart item quantity"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Parse request data
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data',
                'errors': {'json': ['Request body contains invalid JSON']}
            }, status=400)
        
        quantity = data.get('quantity')
        
        if not quantity:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields',
                'errors': {'quantity': ['Quantity is required']}
            }, status=400)
        
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity',
                'errors': {'quantity': ['Quantity must be a positive integer']}
            }, status=400)
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=user)
        
        # Check inventory
        if quantity > cart_item.product.inventory:
            return JsonResponse({
                'success': False,
                'message': 'Insufficient inventory',
                'errors': {'inventory': [f'Only {cart_item.product.inventory} items available']}
            }, status=400)
        
        # Update quantity
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart item updated successfully',
            'data': {
                'cart_item_id': cart_item.id,
                'product_id': cart_item.product.id,
                'quantity': cart_item.quantity,
                'subtotal': float(cart_item.subtotal()),
                'total_items': cart_item.cart.total_items(),
                'total_price': float(cart_item.cart.total_price())
            }
        }, status=200)
        
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart item not found',
            'errors': {'cart_item': ['Item not found in your cart']}
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error updating cart item',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['DELETE', 'POST'])
def remove_from_cart_api(request, item_id):
    """API endpoint to remove item from cart"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Get cart item
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=user)
        product_title = cart_item.product.title
        cart = cart_item.cart
        
        # Delete cart item
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{product_title} removed from cart',
            'data': {
                'removed_item_id': item_id,
                'total_items': cart.total_items(),
                'total_price': float(cart.total_price())
            }
        }, status=200)
        
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart item not found',
            'errors': {'cart_item': ['Item not found in your cart']}
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error removing item from cart',
            'errors': {'server': [str(e)]}
        }, status=500)


@csrf_exempt
@require_http_methods(['POST', 'DELETE'])
def clear_cart_api(request):
    """API endpoint to clear all items from cart"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Get cart
        cart = get_object_or_404(Cart, user=user)
        
        # Get count before clearing
        items_count = cart.total_items()
        
        # Clear cart
        cart.clear()
        
        return JsonResponse({
            'success': True,
            'message': f'Cart cleared. {items_count} items removed.',
            'data': {
                'items_removed': items_count,
                'total_items': 0,
                'total_price': 0.00
            }
        }, status=200)
        
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': True,
            'message': 'Cart is already empty',
            'data': {
                'items_removed': 0,
                'total_items': 0,
                'total_price': 0.00
            }
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error clearing cart',
            'errors': {'server': [str(e)]}
        }, status=500)

