from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from posts.models import Post, Bookmark
from products.models import Purchase, ProductImage
from authentication.qr_utils import update_user_qr_code
from authentication.utils import get_token_user
from authentication.decorators import jwt_required
from authentication.serializers_helpers import serialize_post, serialize_purchase

@csrf_exempt
@require_http_methods(['GET'])
def categories_api(request):
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
            # Create the main product (no post_type needed since all posts are products now)
            post = Post(
                title=title,
                description=description,
                image=main_image,
                user=request.user,
                price=price,
                category=category,
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
        
        # Validate category
        valid_categories = [choice[0] for choice in Post.CATEGORY_CHOICES]
        if category and category not in valid_categories:
            return JsonResponse({
                'success': False,
                'message': 'Invalid category',
                'errors': {'category': [f'Must be one of: {", ".join(valid_categories)}']}
            }, status=400)
        
        # Create product
        post = Post(
            title=title,
            description=description,
            image=main_image,
            user=user,
            price=price_decimal,
            category=category or 'other',
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
        category = request.POST.get('category', post.category)
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
        
        # Validate category if provided
        if category:
            valid_categories = [choice[0] for choice in Post.CATEGORY_CHOICES]
            if category not in valid_categories:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid category',
                    'errors': {'category': [f'Must be one of: {", ".join(valid_categories)}']}
                }, status=400)
            post.category = category
        
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

