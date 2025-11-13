from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from users.models import User
from products.models import Purchase
from posts.models import Post
from .qr_utils import decode_qr_data, get_user_purchases_from_qr
from .otp_utils import create_otp, verify_otp as verify_otp_util
from .utils import get_token_user
import json
from django.db.models import Sum, Count, Avg
from decimal import Decimal

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
