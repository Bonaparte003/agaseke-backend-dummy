from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from posts.models import Post, Bookmark, Category
from products.models import Purchase, ProductImage
from authentication.qr_utils import update_user_qr_code
from authentication.utils import get_token_user
from authentication.decorators import jwt_required
from authentication.serializers_helpers import serialize_post, serialize_purchase

@csrf_exempt
@require_http_methods(['GET'])
def categories_api(request):
    """API endpoint to get all available categories with images"""
    try:
        # Get all active categories from database
        categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
        
        categories_data = []
        for category in categories:
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'category_image': category.category_image.url if category.category_image else None,
                'product_count': category.product_count(),
                'display_order': category.display_order
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
def purchase_product(request, post_id):
    """Legacy HTML view - kept for backward compatibility"""
    if request.method == 'POST':
        product = get_object_or_404(Post, id=post_id)
        
        # Check if user is trying to buy their own product
        if product.user == request.user:
            messages.error(request, "You cannot purchase your own product.")
            return redirect('post_detail', post_id=post_id)
        
        # Check if price is None or not set
        if product.price is None:
            messages.error(request, f'Unable to purchase {product.title}. The product does not have a valid price.')
            return redirect('post_detail', post_id=post_id)
        

        # Check if product is out of stock
        if product.inventory <= 0:
            messages.error(request, f'Sorry, {product.title} is currently out of stock.')
            return redirect('post_detail', post_id=post_id)
        
        # Get quantity from form
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid quantity.")
            return redirect('post_detail', post_id=post_id)
        
        # Check if enough inventory (with fresh data to prevent race conditions)
        product.refresh_from_db()  # Get latest inventory data
        if product.inventory < quantity:
            if product.inventory == 0:
                messages.error(request, f'Sorry, {product.title} is now out of stock.')
            else:
                messages.error(request, f'Sorry, there are only {product.inventory} items available.')
            return redirect('post_detail', post_id=post_id)
        
        # Get delivery method and details
        delivery_method = request.POST.get('delivery_method', 'pickup')
        delivery_address = request.POST.get('delivery_address', '')
        delivery_latitude = request.POST.get('delivery_latitude')
        delivery_longitude = request.POST.get('delivery_longitude')
        payment_method = request.POST.get('payment_method', 'momo')  # New payment method field
        
        # Calculate total price
        total_price = product.price * quantity
        delivery_fee = Decimal('5.00') if delivery_method == 'delivery' else Decimal('0.00')
        
        # Validate delivery details if delivery is selected
        if delivery_method == 'delivery':
            if not delivery_address:
                messages.error(request, "Please provide a delivery address for home delivery.")
                return redirect('post_detail', post_id=post_id)
        
        # Determine initial status based on delivery method
        initial_status = 'awaiting_delivery' if delivery_method == 'delivery' else 'awaiting_pickup'
        
        # Create a new purchase with agaseke workflow
        purchase = Purchase(
            buyer=request.user,
            product=product,
            quantity=quantity,
            purchase_price=total_price,
            delivery_method=delivery_method,
            payment_method=payment_method,
            delivery_fee=delivery_fee,
            delivery_address=delivery_address,
            status=initial_status
        )
        
        # Add location coordinates if provided
        if delivery_latitude and delivery_longitude:
            try:
                purchase.delivery_latitude = float(delivery_latitude)
                purchase.delivery_longitude = float(delivery_longitude)
            except (ValueError, TypeError):
                pass  # Ignore invalid coordinates
        
        purchase.save()
        
        # Update inventory immediately after successful purchase
        product.inventory -= quantity
        
        # Update statistics
        product.total_purchases += 1
        product.save()
        
        # Update QR code to include this purchase
        update_user_qr_code(request.user)
        
        # Success message based on delivery method
        if delivery_method == 'delivery':
            messages.success(request, f'You have successfully purchased {quantity} {product.title}! Total: RWF {total_price + delivery_fee:,.2f} (including RWF {delivery_fee:,.2f} delivery fee). agaseke will deliver to your address.')
        else:
            messages.success(request, f'You have successfully purchased {quantity} {product.title}! Please go to agaseke to collect your items.')
        
        return redirect('purchase_history')
    
    return redirect('post_detail', post_id=post_id)


@csrf_exempt
@require_http_methods(['POST'])
def purchase_product_api(request, post_id):
    """API endpoint to purchase a product"""
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
        try:
            import json
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data',
                'errors': {'json': ['Request body contains invalid JSON']}
            }, status=400)
        
        product = get_object_or_404(Post, id=post_id)
        
        # Check if user is trying to buy their own product
        if product.user == user:
            return JsonResponse({
                'success': False,
                'message': 'Cannot purchase your own product',
                'errors': {'product': ['You cannot purchase your own product']}
            }, status=400)
        
        # Check if price is None or not set
        if product.price is None:
            return JsonResponse({
                'success': False,
                'message': 'Product has no valid price',
                'errors': {'product': ['Product does not have a valid price']}
            }, status=400)
        
        # Check if product is out of stock
        if product.inventory <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Product out of stock',
                'errors': {'product': ['Product is currently out of stock']}
            }, status=400)
        
        # Get quantity
        try:
            quantity = int(data.get('quantity', 1))
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'Invalid quantity',
                'errors': {'quantity': ['Please enter a valid quantity']}
            }, status=400)
        
        # Check if enough inventory
        product.refresh_from_db()
        if product.inventory < quantity:
            return JsonResponse({
                'success': False,
                'message': 'Insufficient inventory',
                'errors': {'inventory': [f'Only {product.inventory} items available']}
            }, status=400)
        
        # Get delivery method and details
        delivery_method = data.get('delivery_method', 'pickup')
        delivery_address = data.get('delivery_address', '')
        delivery_latitude = data.get('delivery_latitude')
        delivery_longitude = data.get('delivery_longitude')
        payment_method = data.get('payment_method', 'momo')
        
        # Validate delivery method
        if delivery_method not in ['pickup', 'delivery']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid delivery method',
                'errors': {'delivery_method': ['Must be either "pickup" or "delivery"']}
            }, status=400)
        
        # Calculate total price
        total_price = product.price * quantity
        delivery_fee = Decimal('5.00') if delivery_method == 'delivery' else Decimal('0.00')
        
        # Validate delivery details if delivery is selected
        if delivery_method == 'delivery':
            if not delivery_address:
                return JsonResponse({
                    'success': False,
                    'message': 'Delivery address required',
                    'errors': {'delivery_address': ['Please provide a delivery address']}
                }, status=400)
        
        # Determine initial status
        initial_status = 'awaiting_delivery' if delivery_method == 'delivery' else 'awaiting_pickup'
        
        # Create purchase
        purchase = Purchase(
            buyer=user,
            product=product,
            quantity=quantity,
            purchase_price=total_price,
            delivery_method=delivery_method,
            payment_method=payment_method,
            delivery_fee=delivery_fee,
            delivery_address=delivery_address,
            status=initial_status
        )
        
        # Add location coordinates if provided
        if delivery_latitude and delivery_longitude:
            try:
                purchase.delivery_latitude = float(delivery_latitude)
                purchase.delivery_longitude = float(delivery_longitude)
            except (ValueError, TypeError):
                pass
        
        purchase.save()
        
        # Update inventory
        product.inventory -= quantity
        product.total_purchases += 1
        product.save()
        
        # Update QR code
        update_user_qr_code(user)
        
        # Serialize purchase for response
        purchase_data = serialize_purchase(purchase)
        
        return JsonResponse({
            'success': True,
            'message': f'Purchase created successfully. Total: RWF {float(total_price + delivery_fee):,.2f}',
            'data': purchase_data
        }, status=201)
        
    except Post.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found',
            'errors': {'product': ['Product with this ID does not exist']}
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error creating purchase',
            'errors': {'server': [str(e)]}
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def bulk_purchase_api(request):
    """
    API endpoint for bulk purchase - purchase multiple products at once
    
    Can work in two modes:
    1. Purchase from cart (set "from_cart": true)
    2. Purchase specific items (provide "items" array)
    
    Request body:
    {
        "from_cart": true/false,
        "items": [  // Only needed if from_cart is false
            {"product_id": 1, "quantity": 2},
            {"product_id": 3, "quantity": 1}
        ],
        "delivery_method": "pickup" or "delivery",
        "payment_method": "momo" or "credit",
        "delivery_address": "123 Main St" (required if delivery_method is "delivery"),
        "delivery_latitude": 12.345,
        "delivery_longitude": 67.890,
        "clear_cart": true/false  // Clear cart after purchase (default: true if from_cart)
    }
    """
    try:
        from django.db import transaction
        from decimal import Decimal
        import json
        
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Parse request data
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data',
                'errors': {'json': ['Request body contains invalid JSON']}
            }, status=400)
        
        from_cart = data.get('from_cart', False)
        delivery_method = data.get('delivery_method', 'pickup')
        payment_method = data.get('payment_method', 'momo')
        delivery_address = data.get('delivery_address', '')
        delivery_latitude = data.get('delivery_latitude')
        delivery_longitude = data.get('delivery_longitude')
        clear_cart = data.get('clear_cart', from_cart)  # Default to True if purchasing from cart
        
        # Validate delivery method
        if delivery_method not in ['pickup', 'delivery']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid delivery method',
                'errors': {'delivery_method': ['Must be "pickup" or "delivery"']}
            }, status=400)
        
        # Validate delivery address for delivery method
        if delivery_method == 'delivery' and not delivery_address:
            return JsonResponse({
                'success': False,
                'message': 'Delivery address required',
                'errors': {'delivery_address': ['Please provide a delivery address for home delivery']}
            }, status=400)
        
        # Get items to purchase
        items_to_purchase = []
        
        if from_cart:
            # Purchase from cart
            from products.models import Cart, CartItem
            try:
                cart = Cart.objects.get(user=user)
                cart_items = cart.items.select_related('product').all()
                
                if not cart_items.exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'Cart is empty',
                        'errors': {'cart': ['Your cart is empty']}
                    }, status=400)
                
                for cart_item in cart_items:
                    items_to_purchase.append({
                        'product': cart_item.product,
                        'quantity': cart_item.quantity
                    })
                    
            except Cart.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Cart not found',
                    'errors': {'cart': ['Cart does not exist']}
                }, status=404)
        else:
            # Purchase specific items
            items_data = data.get('items', [])
            
            if not items_data:
                return JsonResponse({
                    'success': False,
                    'message': 'No items provided',
                    'errors': {'items': ['Please provide items to purchase']}
                }, status=400)
            
            # Validate and fetch products
            for item_data in items_data:
                product_id = item_data.get('product_id')
                quantity = item_data.get('quantity', 1)
                
                if not product_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Product ID required',
                        'errors': {'items': ['Each item must have a product_id']}
                    }, status=400)
                
                try:
                    quantity = int(quantity)
                    if quantity <= 0:
                        raise ValueError("Quantity must be positive")
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid quantity',
                        'errors': {'items': [f'Invalid quantity for product {product_id}']}
                    }, status=400)
                
                try:
                    product = Post.objects.get(id=product_id)
                    items_to_purchase.append({
                        'product': product,
                        'quantity': quantity
                    })
                except Post.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Product not found',
                        'errors': {'items': [f'Product with ID {product_id} not found']}
                    }, status=404)
        
        # Validation checks before creating purchases
        validation_errors = []
        
        for item in items_to_purchase:
            product = item['product']
            quantity = item['quantity']
            
            # Check if buying own product
            if product.user == user:
                validation_errors.append(f'Cannot purchase your own product: {product.title}')
            
            # Check if product has valid price
            if product.price is None:
                validation_errors.append(f'{product.title} does not have a valid price')
            
            # Check inventory
            if product.inventory < quantity:
                if product.inventory == 0:
                    validation_errors.append(f'{product.title} is out of stock')
                else:
                    validation_errors.append(f'{product.title}: only {product.inventory} available, requested {quantity}')
        
        if validation_errors:
            return JsonResponse({
                'success': False,
                'message': 'Validation failed',
                'errors': {'items': validation_errors}
            }, status=400)
        
        # Use database transaction for atomic operation
        created_purchases = []
        total_amount = Decimal('0.00')
        delivery_fee = Decimal('5.00') if delivery_method == 'delivery' else Decimal('0.00')
        initial_status = 'awaiting_delivery' if delivery_method == 'delivery' else 'awaiting_pickup'
        
        with transaction.atomic():
            # Create purchases for each item
            for item in items_to_purchase:
                product = item['product']
                quantity = item['quantity']
                
                # Refresh product to get latest inventory (prevent race conditions)
                product.refresh_from_db()
                
                # Double-check inventory
                if product.inventory < quantity:
                    raise ValueError(f'Insufficient inventory for {product.title}')
                
                # Calculate price for this item
                item_total = product.price * quantity
                total_amount += item_total
                
                # Create purchase
                purchase = Purchase(
                    buyer=user,
                    product=product,
                    quantity=quantity,
                    purchase_price=item_total,
                    delivery_method=delivery_method,
                    payment_method=payment_method,
                    delivery_fee=delivery_fee if len(items_to_purchase) == 1 or item == items_to_purchase[-1] else Decimal('0.00'),  # Add delivery fee to last item only
                    delivery_address=delivery_address,
                    status=initial_status
                )
                
                # Add location coordinates if provided
                if delivery_latitude and delivery_longitude:
                    try:
                        purchase.delivery_latitude = float(delivery_latitude)
                        purchase.delivery_longitude = float(delivery_longitude)
                    except (ValueError, TypeError):
                        pass
                
                purchase.save()
                created_purchases.append(purchase)
                
                # Update product inventory and stats
                product.inventory -= quantity
                product.total_purchases += 1
                product.save()
            
            # Clear cart if requested
            if clear_cart and from_cart:
                cart.clear()
        
        # Update user's QR code after all purchases
        update_user_qr_code(user)
        
        # Prepare response data
        purchases_data = [serialize_purchase(purchase) for purchase in created_purchases]
        
        # Calculate summary
        total_with_delivery = total_amount + delivery_fee
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully purchased {len(created_purchases)} item(s). Total: RWF {float(total_with_delivery):,.2f}',
            'data': {
                'purchases': purchases_data,
                'summary': {
                    'total_items': len(created_purchases),
                    'total_quantity': sum(p.quantity for p in created_purchases),
                    'subtotal': float(total_amount),
                    'delivery_fee': float(delivery_fee),
                    'total': float(total_with_delivery),
                    'delivery_method': delivery_method,
                    'payment_method': payment_method,
                    'cart_cleared': clear_cart and from_cart
                }
            }
        }, status=201)
        
    except ValueError as e:
        # Inventory check failed during transaction
        return JsonResponse({
            'success': False,
            'message': 'Purchase failed',
            'errors': {'transaction': [str(e)]}
        }, status=400)
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Bulk purchase error: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'message': 'Error processing purchase',
            'errors': {'server': [str(e)]}
        }, status=500)


@login_required
def create_product(request):
    """Legacy HTML view - kept for backward compatibility"""
    # Check if user has vendor role
    if not request.user.is_vendor_role:
        messages.error(request, 'You need to upgrade your account to Vendor status to create product listings.')
        return redirect('user_settings')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        main_image = request.FILES.get('main_image')
        price = request.POST.get('price')
        category = request.POST.get('category')
        inventory = request.POST.get('inventory', 1)
        
        try:
            inventory = int(inventory)
            if inventory < 0:
                inventory = 1
        except (ValueError, TypeError):
            inventory = 1
        
        if title and description and main_image and price:
            # Get category object
            category_obj = None
            if category:
                try:
                    category_id = int(category)
                    category_obj = Category.objects.get(id=category_id, is_active=True)
                except (ValueError, Category.DoesNotExist):
                    try:
                        category_obj = Category.objects.get(slug=category, is_active=True)
                    except Category.DoesNotExist:
                        pass
            
            # Create the main product (no post_type needed since all posts are products now)
            post = Post(
                title=title,
                description=description,
                image=main_image,
                user=request.user,
                price=price,
                category=category_obj,
                inventory=inventory
            )
            post.save()
            
            # Process auxiliary images (limit to 5)
            auxiliary_images = request.FILES.getlist('auxiliary_images')
            print(f"DEBUG: Found {len(auxiliary_images)} auxiliary images in create_product")
            max_images = min(len(auxiliary_images), 5)  # Limit to 5 images
            
            for i in range(max_images):
                print(f"DEBUG: Creating auxiliary image {i+1} of {max_images}")
                ProductImage.objects.create(
                    product=post,
                    image=auxiliary_images[i],
                    display_order=i
                )
                
            messages.success(request, 'Product listing created successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fill all required fields')
    
    return render(request, 'authentication/create_product.html')


@csrf_exempt
@require_http_methods(['POST'])
def create_product_api(request):
    """API endpoint to create a product"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Check if user is a vendor
        if not user.is_vendor_role:
            return JsonResponse({
                'success': False,
                'message': 'Vendor role required',
                'errors': {'role': ['You need to be a vendor to create products']}
            }, status=403)
        
        # Parse request data (support both JSON and form-data for file uploads)
        if request.content_type and 'application/json' in request.content_type:
            try:
                import json
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data',
                    'errors': {'json': ['Request body contains invalid JSON']}
                }, status=400)
            # For JSON, we'd need base64 encoded images - not ideal, so we'll use form-data
            return JsonResponse({
                'success': False,
                'message': 'Use multipart/form-data for file uploads',
                'errors': {'content_type': ['Please use multipart/form-data for product creation with images']}
            }, status=400)
        else:
            # Form data (for file uploads)
            title = request.POST.get('title')
            description = request.POST.get('description')
            main_image = request.FILES.get('main_image')
            price = request.POST.get('price')
            category = request.POST.get('category')
            inventory = request.POST.get('inventory', 1)
        
        # Validate required fields
        if not title or not description or not main_image or not price:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields',
                'errors': {
                    'title': ['Required'] if not title else [],
                    'description': ['Required'] if not description else [],
                    'main_image': ['Required'] if not main_image else [],
                    'price': ['Required'] if not price else [],
                }
            }, status=400)
        
        # Validate price
        try:
            price_decimal = Decimal(str(price))
            if price_decimal <= 0:
                raise ValueError("Price must be positive")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'Invalid price',
                'errors': {'price': ['Price must be a positive number']}
            }, status=400)
        
        # Validate inventory
        try:
            inventory = int(inventory)
            if inventory < 0:
                inventory = 1
        except (ValueError, TypeError):
            inventory = 1
        
        # Validate and get category
        category_obj = None
        if category:
            # Try to get category by ID first, then by slug
            try:
                category_id = int(category)
                category_obj = Category.objects.get(id=category_id, is_active=True)
            except (ValueError, Category.DoesNotExist):
                # Try by slug
                try:
                    category_obj = Category.objects.get(slug=category, is_active=True)
                except Category.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid category',
                        'errors': {'category': ['Category not found or inactive']}
                    }, status=400)
        else:
            # Default to 'other' category if not provided
            try:
                category_obj = Category.objects.get(slug='other')
            except Category.DoesNotExist:
                pass
        
        # Handle great_deal fields
        is_great_deal = request.POST.get('is_great_deal', 'false').lower() == 'true'
        original_price = request.POST.get('original_price')
        original_price_decimal = None
        
        if is_great_deal and original_price:
            try:
                original_price_decimal = Decimal(str(original_price))
                if original_price_decimal <= price_decimal:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid pricing',
                        'errors': {'original_price': ['Original price must be greater than discounted price']}
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid original price',
                    'errors': {'original_price': ['Original price must be a valid number']}
                }, status=400)
        
        # Create product
        post = Post(
            title=title,
            description=description,
            image=main_image,
            user=user,
            price=price_decimal,
            is_great_deal=is_great_deal,
            original_price=original_price_decimal if is_great_deal else None,
            category=category_obj,
            inventory=inventory
        )
        post.save()
        
        # Process auxiliary images (limit to 5)
        auxiliary_images = request.FILES.getlist('auxiliary_images')
        max_images = min(len(auxiliary_images), 5)
        
        for i in range(max_images):
            ProductImage.objects.create(
                product=post,
                image=auxiliary_images[i],
                display_order=i
            )
        
        # Serialize and return
        post_data = serialize_post(post, user)
        
        return JsonResponse({
            'success': True,
            'message': 'Product created successfully',
            'data': post_data
        }, status=201)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error creating product',
            'errors': {'server': [str(e)]}
        }, status=500)

@csrf_exempt
@require_http_methods(['PUT', 'PATCH'])
def edit_product_api(request, post_id):
    """API endpoint to edit/update a product"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Check if user is a vendor
        if not user.is_vendor_role:
            return JsonResponse({
                'success': False,
                'message': 'Vendor role required',
                'errors': {'role': ['You need to be a vendor to edit products']}
            }, status=403)
        
        # Get the product
        try:
            post = Post.objects.get(id=post_id, user=user)
        except Post.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Product not found',
                'errors': {'product': ['Product not found or you do not have permission to edit it']}
            }, status=404)
        
        # Business Rule: Check if product has been purchased or bookmarked
        has_purchases = Purchase.objects.filter(product=post).exists()
        has_bookmarks = Bookmark.objects.filter(post=post).exists()
        
        if has_purchases or has_bookmarks:
            return JsonResponse({
                'success': False,
                'message': 'Cannot edit this product',
                'errors': {'product': ['This product cannot be edited as it has been purchased or bookmarked by customers']}
            }, status=403)
        
        # Parse request data (support form-data for file uploads)
        if request.content_type and 'application/json' in request.content_type:
            return JsonResponse({
                'success': False,
                'message': 'Use multipart/form-data for file uploads',
                'errors': {'content_type': ['Please use multipart/form-data for product updates with images']}
            }, status=400)
        
        # Get form data
        title = request.POST.get('title', post.title)
        description = request.POST.get('description', post.description)
        price = request.POST.get('price', post.price)
        category_input = request.POST.get('category')
        inventory = request.POST.get('inventory', post.inventory)
        main_image = request.FILES.get('main_image')  # Optional for updates
        
        # Validate price if provided
        if price:
            try:
                price_decimal = Decimal(str(price))
                if price_decimal <= 0:
                    raise ValueError("Price must be positive")
                post.price = price_decimal
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid price',
                    'errors': {'price': ['Price must be a positive number']}
                }, status=400)
        
        # Validate inventory if provided
        if inventory:
            try:
                inventory_int = int(inventory)
                if inventory_int < 0:
                    inventory_int = 0
                post.inventory = inventory_int
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid inventory',
                    'errors': {'inventory': ['Inventory must be a non-negative integer']}
                }, status=400)
        
        # Validate and update category if provided
        if category_input:
            try:
                # Try to get category by ID first, then by slug
                try:
                    category_id = int(category_input)
                    category_obj = Category.objects.get(id=category_id, is_active=True)
                    post.category = category_obj
                except (ValueError, Category.DoesNotExist):
                    # Try by slug
                    try:
                        category_obj = Category.objects.get(slug=category_input, is_active=True)
                        post.category = category_obj
                    except Category.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'message': 'Invalid category',
                            'errors': {'category': ['Category not found or inactive']}
                        }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': 'Error updating category',
                    'errors': {'category': [str(e)]}
                }, status=400)
        
        # Handle great_deal fields
        is_great_deal_input = request.POST.get('is_great_deal')
        if is_great_deal_input is not None:
            post.is_great_deal = is_great_deal_input.lower() == 'true'
        
        original_price_input = request.POST.get('original_price')
        if original_price_input:
            try:
                original_price_decimal = Decimal(str(original_price_input))
                if post.is_great_deal and original_price_decimal <= post.price:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid pricing',
                        'errors': {'original_price': ['Original price must be greater than discounted price']}
                    }, status=400)
                post.original_price = original_price_decimal
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid original price',
                    'errors': {'original_price': ['Original price must be a valid number']}
                }, status=400)
        
        # If great_deal is disabled, clear original_price
        if not post.is_great_deal:
            post.original_price = None
        
        # Update fields
        post.title = title
        post.description = description
        
        # Update main image if provided
        if main_image:
            post.image = main_image
        
        post.save()
        
        # Handle auxiliary images if provided
        auxiliary_images = request.FILES.getlist('auxiliary_images')
        if auxiliary_images:
            # Remove old auxiliary images
            ProductImage.objects.filter(product=post).delete()
            
            # Add new ones (limit to 5)
            max_images = min(len(auxiliary_images), 5)
            for i in range(max_images):
                ProductImage.objects.create(
                    product=post,
                    image=auxiliary_images[i],
                    display_order=i
                )
        
        # Serialize and return
        post_data = serialize_post(post, user)
        
        return JsonResponse({
            'success': True,
            'message': 'Product updated successfully',
            'data': post_data
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error updating product',
            'errors': {'server': [str(e)]}
        }, status=500)

@csrf_exempt
@require_http_methods(['DELETE', 'POST'])
def delete_product_api(request, post_id):
    """API endpoint to delete a product"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Check if user is a vendor
        if not user.is_vendor_role:
            return JsonResponse({
                'success': False,
                'message': 'Vendor role required',
                'errors': {'role': ['You need to be a vendor to delete products']}
            }, status=403)
        
        # Get the product
        try:
            post = Post.objects.get(id=post_id, user=user)
        except Post.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Product not found',
                'errors': {'product': ['Product not found or you do not have permission to delete it']}
            }, status=404)
        
        # Business Rule: Check if product has been purchased
        has_purchases = Purchase.objects.filter(product=post).exists()
        
        if has_purchases:
            return JsonResponse({
                'success': False,
                'message': 'Cannot delete this product',
                'errors': {'product': ['This product cannot be deleted as it has purchase history']}
            }, status=403)
        
        # Store product info before deletion
        product_info = {
            'id': post.id,
            'title': post.title,
            'price': str(post.price)
        }
        
        # Delete the product
        post.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Product deleted successfully',
            'data': {
                'deleted_product': product_info
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error deleting product',
            'errors': {'server': [str(e)]}
        }, status=500)

@csrf_exempt
@require_http_methods(['GET'])
def my_products_api(request):
    """
    API endpoint to get all products created by the vendor with management info
    
    Query parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 50, max: 100)
    - category: Filter by category slug or ID
    - in_stock: Filter by stock status (true/false)
    - is_great_deal: Filter by great deal status (true/false)
    - search: Search in title and description
    - sort: Sort field (created_at, -created_at, price, -price, title, inventory)
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
        
        # Check if user is a vendor
        if not user.is_vendor_role:
            return JsonResponse({
                'success': False,
                'message': 'Vendor role required',
                'errors': {'role': ['You need to be a vendor to access this endpoint']}
            }, status=403)
        
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 per page
        category_filter = request.GET.get('category')
        in_stock_filter = request.GET.get('in_stock')
        is_great_deal_filter = request.GET.get('is_great_deal')
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', '-created_at')
        
        # Start with user's products
        products = Post.objects.filter(user=user).select_related('category')
        
        # Apply filters
        if category_filter:
            # Try by ID first, then by slug
            try:
                category_id = int(category_filter)
                products = products.filter(category_id=category_id)
            except ValueError:
                products = products.filter(category__slug=category_filter)
        
        if in_stock_filter is not None:
            if in_stock_filter.lower() == 'true':
                products = products.filter(inventory__gt=0)
            elif in_stock_filter.lower() == 'false':
                products = products.filter(inventory=0)
        
        if is_great_deal_filter is not None:
            if is_great_deal_filter.lower() == 'true':
                products = products.filter(is_great_deal=True)
            elif is_great_deal_filter.lower() == 'false':
                products = products.filter(is_great_deal=False)
        
        if search_query:
            from django.db.models import Q
            products = products.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Apply sorting
        valid_sort_fields = ['created_at', '-created_at', 'price', '-price', 'title', '-title', 'inventory', '-inventory']
        if sort_by in valid_sort_fields:
            products = products.order_by(sort_by)
        else:
            products = products.order_by('-created_at')
        
        # Get total count before pagination
        total_count = products.count()
        
        # Calculate pagination
        start = (page - 1) * limit
        end = start + limit
        paginated_products = products[start:end]
        
        # Serialize products with management info
        products_data = []
        for product in paginated_products:
            # Check if product can be edited or deleted
            has_purchases = Purchase.objects.filter(product=product).exists()
            has_bookmarks = Bookmark.objects.filter(post=product).exists()
            
            can_edit = not (has_purchases or has_bookmarks)
            can_delete = not has_purchases  # Can only delete if never purchased
            
            product_data = serialize_post(product, user)
            
            # Add management metadata
            product_data['management'] = {
                'can_edit': can_edit,
                'can_delete': can_delete,
                'has_purchases': has_purchases,
                'has_bookmarks': has_bookmarks,
                'edit_restrictions': [] if can_edit else ['Product has been purchased or bookmarked'],
                'delete_restrictions': [] if can_delete else ['Product has purchase history']
            }
            
            products_data.append(product_data)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_previous = page > 1
        
        return JsonResponse({
            'success': True,
            'message': f'Retrieved {len(products_data)} product(s)',
            'data': {
                'products': products_data,
                'pagination': {
                    'current_page': page,
                    'per_page': limit,
                    'total_items': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'next_page': page + 1 if has_next else None,
                    'previous_page': page - 1 if has_previous else None
                },
                'filters_applied': {
                    'category': category_filter,
                    'in_stock': in_stock_filter,
                    'is_great_deal': is_great_deal_filter,
                    'search': search_query,
                    'sort': sort_by
                }
            }
        }, status=200)
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': 'Invalid parameter',
            'errors': {'params': [str(e)]}
        }, status=400)
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"My products API error: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving products',
            'errors': {'server': [str(e)]}
        }, status=500)


@login_required
def edit_product(request, product_id):
    # Check if user has vendor role
    if not request.user.is_vendor_role:
        messages.error(request, 'You need to have Vendor status to edit product listings.')
        return redirect('dashboard')
    
    # Get the product (ensure it belongs to the user)
    product = get_object_or_404(Post, id=product_id, user=request.user)
    
    # Business Rule: Check if product has been purchased or bookmarked
    has_purchases = Purchase.objects.filter(product=product).exists()
    has_bookmarks = Bookmark.objects.filter(post=product).exists()
    
    if has_purchases or has_bookmarks:
        messages.error(request, 'This product cannot be edited as it has been purchased or bookmarked by customers.')
        return redirect('vendor_dashboard')
    
    # Get existing auxiliary images
    auxiliary_images = ProductImage.objects.filter(product=product).order_by('display_order')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category = request.POST.get('category')
        inventory = request.POST.get('inventory')
        
        if title and description and price:
            # Update product details
            product.title = title
            product.description = description
            product.price = price
            product.category = category
            
            # Update inventory if provided
            if inventory:
                try:
                    inventory_value = int(inventory)
                    if inventory_value >= 0:
                        product.inventory = inventory_value
                except (ValueError, TypeError):
                    pass  # Keep existing inventory if invalid value
            
            # Handle main image update if provided
            main_image = request.FILES.get('main_image')
            if main_image:
                product.image = main_image
            
            product.save()
            
            # Handle auxiliary images
            # Check if any auxiliary images should be deleted
            images_to_keep = request.POST.getlist('keep_auxiliary_image')
            
            # Delete images not in the keep list
            for aux_image in auxiliary_images:
                if str(aux_image.id) not in images_to_keep:
                    aux_image.delete()
            
            # Count remaining images after deletion
            remaining_images_count = ProductImage.objects.filter(product=product).count()
            
            # Calculate how many new images we can add
            max_new_images = 5 - remaining_images_count
            
            if max_new_images > 0:
                # Add new auxiliary images up to the allowed limit
                new_auxiliary_images = request.FILES.getlist('auxiliary_images')
                print(f"DEBUG: Found {len(new_auxiliary_images)} new auxiliary images")
                max_to_add = min(len(new_auxiliary_images), max_new_images)
                
                for i in range(max_to_add):
                    print(f"DEBUG: Creating auxiliary image {i+1} of {max_to_add}")
                    ProductImage.objects.create(
                        product=product,
                        image=new_auxiliary_images[i],
                        display_order=remaining_images_count + i
                    )
            
            messages.success(request, 'Product updated successfully!')
            return redirect('vendor_dashboard')
        else:
            messages.error(request, 'Please fill all required fields')
    
    context = {
        'product': product,
        'auxiliary_images': auxiliary_images
    }
    
    return render(request, 'authentication/edit_product.html', context)

