from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from users.models import User
from products.models import Purchase
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
