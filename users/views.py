import csv
from datetime import datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.models import User
from posts.models import Post
from products.models import Purchase
from authentication.utils import generate_csv_report, generate_pdf_report, get_token_user
from authentication.serializers_helpers import serialize_purchase, serialize_user

@login_required
def purchase_history(request):
    """Legacy HTML view - kept for backward compatibility"""
    purchases = Purchase.objects.filter(buyer=request.user).order_by('-created_at')
    
    # Check if export is requested
    export_format = request.GET.get('export')
    if export_format in ['csv', 'pdf']:
        # Prepare data for export
        headers = ['Order ID', 'Product', 'Seller', 'Date', 'Price', 'Status', 'Quantity', 'Delivery Method']
        data = []
        
        for purchase in purchases:
            data.append([
                purchase.order_id,
                purchase.product.title,
                f"{purchase.product.user.first_name} {purchase.product.user.last_name}",
                purchase.created_at.strftime('%Y-%m-%d %H:%M'),
                f"RWF {purchase.purchase_price:,.1f}",
                purchase.status.title(),
                purchase.quantity,
                purchase.delivery_method.title()
            ])
        
        # Summary data for PDF
        summary_data = {
            'Total Purchases': purchases.count(),
            'Total Spent': f"RWF {(purchases.aggregate(total=Sum('purchase_price'))['total'] or 0):,.1f}",
            'Completed Orders': purchases.filter(status='completed').count(),
            'Pending Orders': purchases.filter(status__in=['pending', 'processing']).count(),
            'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        filename = f"purchase_history_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        title = f"Purchase History Report - {request.user.get_full_name() or request.user.username}"
        
        if export_format == 'csv':
            return generate_csv_report(data, filename, headers)
        elif export_format == 'pdf':
            return generate_pdf_report(data, filename, title, headers, summary_data)
    
    context = {
        'purchases': purchases
    }
    
    return render(request, 'authentication/purchase_history.html', context)


@csrf_exempt
@require_http_methods(['GET'])
def purchase_history_api(request):
    """API endpoint to get user's purchase history"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        purchases = Purchase.objects.filter(buyer=user).order_by('-created_at')
        
        # Pagination
        from django.core.paginator import Paginator
        page_number = request.GET.get('page', 1)
        page_size = int(request.GET.get('page_size', 20))
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 20
        
        paginator = Paginator(purchases, page_size)
        try:
            page_obj = paginator.get_page(page_number)
        except:
            page_obj = paginator.get_page(1)
        
        # Serialize purchases
        purchases_data = [serialize_purchase(purchase) for purchase in page_obj]
        
        # Calculate statistics
        total_spent = purchases.aggregate(total=Sum('purchase_price'))['total'] or 0
        completed_count = purchases.filter(status='completed').count()
        pending_count = purchases.filter(status__in=['pending', 'processing', 'awaiting_pickup', 'awaiting_delivery']).count()
        
        return JsonResponse({
            'success': True,
            'message': 'Purchase history retrieved successfully',
            'data': {
                'purchases': purchases_data,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'page_size': page_size,
                    'total_items': purchases.count(),
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                },
                'statistics': {
                    'total_purchases': purchases.count(),
                    'total_spent': float(total_spent),
                    'completed_orders': completed_count,
                    'pending_orders': pending_count,
                }
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving purchase history',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def vendor_dashboard(request):
    """Legacy HTML view - kept for backward compatibility"""
    # Ensure user is a vendor
    if not request.user.is_vendor_role:
        messages.error(request, 'You need to be registered as a vendor to access this dashboard.')
        return redirect('dashboard')
    
    # Get vendor's products
    products = Post.objects.filter(user=request.user)
    
    # Get purchases for vendor's products
    purchases = Purchase.objects.filter(product__user=request.user)
    
    # Calculate statistics
    total_sales = purchases.filter(status='completed').count()
    total_revenue = request.user.total_sales
    
    # Get recent purchases
    recent_purchases = purchases.order_by('-created_at')[:5]
    
    context = {
        'products': products,
        'purchases': purchases,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'recent_purchases': recent_purchases
    }
    
    return render(request, 'authentication/vendor_dashboard.html', context)


@csrf_exempt
@require_http_methods(['GET'])
def vendor_dashboard_api(request):
    """API endpoint to get vendor dashboard data"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Ensure user is a vendor
        if not user.is_vendor_role:
            return JsonResponse({
                'success': False,
                'message': 'Vendor role required',
                'errors': {'role': ['You need to be a vendor to access this dashboard']}
            }, status=403)
        
        # Get vendor's products
        products = Post.objects.filter(user=user)
        
        # Get purchases for vendor's products
        purchases = Purchase.objects.filter(product__user=user)
        
        # Calculate statistics
        completed_purchases = purchases.filter(status='completed')
        total_sales = completed_purchases.count()
        total_revenue = float(user.total_sales) if user.total_sales else 0.0
        
        # Monthly statistics
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_purchases = completed_purchases.filter(
            pickup_confirmed_at__month=current_month,
            pickup_confirmed_at__year=current_year
        )
        monthly_revenue = float(monthly_purchases.aggregate(total=Sum('vendor_payment_amount'))['total'] or 0)
        monthly_sales = monthly_purchases.count()
        
        # Get recent purchases
        recent_purchases = purchases.order_by('-created_at')[:10]
        recent_purchases_data = [serialize_purchase(p) for p in recent_purchases]
        
        # Serialize products
        from authentication.serializers_helpers import serialize_post
        products_data = [serialize_post(product, user) for product in products[:20]]  # Limit to 20 for response
        
        return JsonResponse({
            'success': True,
            'message': 'Vendor dashboard data retrieved successfully',
            'data': {
                'vendor': serialize_user(user),
                'statistics': {
                    'total_products': products.count(),
                    'total_sales': total_sales,
                    'total_revenue': total_revenue,
                    'monthly_revenue': monthly_revenue,
                    'monthly_sales': monthly_sales,
                },
                'products': products_data,
                'recent_purchases': recent_purchases_data,
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error retrieving vendor dashboard',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def user_settings(request):
    """Legacy HTML view - kept for backward compatibility"""
    # Handle form submissions for profile/account updates and role upgrades
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        upgrade_type = request.POST.get('upgrade_type')
        
        # Profile picture upload (AJAX request)
        if form_type == 'profile_picture':
            if 'profile_picture' in request.FILES:
                try:
                    user = request.user
                    user.profile_picture = request.FILES['profile_picture']
                    user.save()
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'message': 'Profile picture updated successfully!'})
                    else:
                        messages.success(request, 'Profile picture updated successfully!')
                        return redirect('user_settings')
                except Exception as e:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': f'Failed to update profile picture: {str(e)}'})
                    else:
                        messages.error(request, f'Failed to update profile picture: {str(e)}')
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'No image file provided'})
                else:
                    messages.error(request, 'No image file provided')
        
        # Profile form submission
        elif form_type == 'profile':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            
            # Update user profile
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.phone_number = phone_number
            
            # Handle profile picture upload if included in the form
            profile_picture = request.FILES.get('profile_picture')
            if profile_picture:
                request.user.profile_picture = profile_picture
            
            request.user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('user_settings')
        
        # Account form submission (password change)
        elif form_type == 'account':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and confirm_password:
                if new_password == confirm_password:
                    request.user.set_password(new_password)
                    request.user.save()
                    messages.success(request, 'Password changed successfully. Please log in again.')
                    return redirect('login')
                else:
                    messages.error(request, 'Passwords do not match.')
            else:
                messages.error(request, 'Please fill in both password fields.')
        
        # Role upgrade form submissions
        elif upgrade_type == 'vendor':
            # Process vendor upgrade
            if request.user.is_vendor_role:
                messages.info(request, 'You are already registered as a vendor.')
            else:
                # Enable vendor role without changing other roles
                request.user.is_vendor_role = True
                request.user.save()
                messages.success(request, 'Congratulations! Your account has been upgraded to include Vendor capabilities. You can now create product posts.')
    
    return render(request, 'authentication/settings.html')


@csrf_exempt
@require_http_methods(['GET', 'PUT', 'PATCH'])
def user_settings_api(request):
    """API endpoint to get/update user settings"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        if request.method == 'GET':
            # Return user settings
            return JsonResponse({
                'success': True,
                'message': 'User settings retrieved successfully',
                'data': serialize_user(user)
            }, status=200)
        
        elif request.method in ['PUT', 'PATCH']:
            # Update user settings
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
            
            # Update profile fields
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'email' in data:
                user.email = data['email']
            if 'phone_number' in data:
                user.phone_number = data['phone_number']
            
            # Handle profile picture if provided (multipart/form-data)
            if 'profile_picture' in request.FILES:
                user.profile_picture = request.FILES['profile_picture']
            
            # Handle password change
            if 'new_password' in data and 'confirm_password' in data:
                if data['new_password'] == data['confirm_password']:
                    user.set_password(data['new_password'])
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Passwords do not match',
                        'errors': {'password': ['Passwords do not match']}
                    }, status=400)
            
            # Handle vendor upgrade
            if 'upgrade_to_vendor' in data and data.get('upgrade_to_vendor') == True:
                if not user.is_vendor_role:
                    user.is_vendor_role = True
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Settings updated successfully',
                'data': serialize_user(user)
            }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error processing request',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def become_vendor(request):
    """Legacy HTML view - kept for backward compatibility"""
    if request.method == 'POST':
        if request.user.is_vendor_role:
            messages.info(request, 'You are already registered as a vendor.')
        else:
            request.user.is_vendor_role = True
            request.user.save()
            messages.success(request, 'Congratulations! Your account has been upgraded to Vendor status. You can now create product posts.')
    
    return redirect('user_settings')


@csrf_exempt
@require_http_methods(['POST'])
def become_vendor_api(request):
    """API endpoint to upgrade user to vendor role"""
    try:
        # Get user from token
        user = get_token_user(request)
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide valid authentication credentials']}
            }, status=401)
        
        # Check if already a vendor
        if user.is_vendor_role:
            return JsonResponse({
                'success': True,
                'message': 'You are already registered as a vendor',
                'data': {
                    'user': serialize_user(user),
                    'is_vendor': True
                }
            }, status=200)
        
        # Upgrade to vendor
        user.is_vendor_role = True
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Congratulations! Your account has been upgraded to Vendor status. You can now create product posts.',
            'data': {
                'user': serialize_user(user),
                'is_vendor': True,
                'upgraded': True
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error upgrading to vendor',
            'errors': {'server': [str(e)]}
        }, status=500)

@login_required
def agaseke_purchase_history(request):
    """View purchase history for agaseke users"""
    if not request.user.is_agaseke():
        messages.error(request, 'Access denied. agaseke role required.')
        return redirect('dashboard')
    
    purchases = Purchase.objects.filter(
        agaseke_user=request.user,
        status='completed'
    ).select_related('buyer', 'product', 'product__user').order_by('-pickup_confirmed_at')
    
    # Pagination could be added here
    context = {
        'purchases': purchases,
        'total_commission': purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
    }
    
    return render(request, 'authentication/agaseke_purchase_history.html', context)

@login_required
def sales_statistics(request):
    """Sales statistics view showing detailed financial breakdown for vendors and agaseke agents"""
    
    # Check if export is requested
    export_format = request.GET.get('export')
    
    if request.user.is_vendor_role:
        # Vendor statistics - show their earnings (80% of product price)
        purchases = Purchase.objects.filter(
            product__user=request.user,
            status='completed'
        ).select_related('product', 'buyer')
        
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
        product_stats = purchases.values('product__title').annotate(
            total_sales=Count('id'),
            total_revenue=Sum('vendor_payment_amount'),
            avg_price=Avg('vendor_payment_amount')
        ).order_by('-total_revenue')
        
        # Recent transactions
        recent_transactions = purchases.order_by('-pickup_confirmed_at')[:10]
        
        # Handle export for vendor
        if export_format in ['csv', 'pdf']:
            if export_format == 'csv':
                headers = ['Product', 'Total Sales', 'Total Revenue', 'Average Price']
                data = []
                for product in product_stats:
                    data.append([
                        product['product__title'],
                        product['total_sales'],
                        f"RWF {product['total_revenue']:,.1f}",
                        f"RWF {product['avg_price']:,.1f}"
                    ])
                filename = f"vendor_sales_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return generate_csv_report(data, filename, headers)
            elif export_format == 'pdf':
                headers = ['Product', 'Total Sales', 'Total Revenue', 'Average Price']
                data = []
                for product in product_stats:
                    data.append([
                        product['product__title'],
                        product['total_sales'],
                        f"RWF {product['total_revenue']:,.1f}",
                        f"RWF {product['avg_price']:,.1f}"
                    ])
                summary_data = {
                    'Total Sales': total_sales,
                    'Total Revenue': f"RWF {total_revenue:,.1f}",
                    'Monthly Revenue': f"RWF {monthly_revenue:,.1f}",
                    'Commission Rate': '80%',
                    'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                filename = f"vendor_sales_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                title = f"Vendor Sales Report - {request.user.get_full_name() or request.user.username}"
                return generate_pdf_report(data, filename, title, headers, summary_data)
        
        context = {
            'user_type': 'vendor',
            'total_sales': total_sales,
            'total_revenue': total_revenue,
            'monthly_revenue': monthly_revenue,
            'monthly_sales': monthly_purchases.count(),
            'product_stats': product_stats,
            'recent_transactions': recent_transactions,
            'commission_rate': 80,  # Vendor gets 80%
            'agaseke_rate': 20,   # agaseke gets 20%
        }
        
    elif request.user.is_agaseke():
        # agaseke agent statistics - show their commission (20% of product price + delivery fees)
        purchases = Purchase.objects.filter(
            agaseke_user=request.user,
            status='completed'
        ).select_related('product', 'buyer', 'product__user')
        
        # Calculate agaseke statistics
        total_transactions = purchases.count()
        total_commission = purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
        
        # Monthly statistics
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_purchases = purchases.filter(
            pickup_confirmed_at__month=current_month,
            pickup_confirmed_at__year=current_year
        )
        monthly_commission = monthly_purchases.aggregate(
            total=Sum('agaseke_commission_amount')
        )['total'] or 0
        
        # Breakdown by commission type
        total_product_price = purchases.aggregate(total=Sum('purchase_price'))['total'] or 0
        total_delivery_fees = purchases.aggregate(total=Sum('delivery_fee'))['total'] or 0
        total_commission_amount = purchases.aggregate(total=Sum('agaseke_commission_amount'))['total'] or 0
        
        commission_breakdown = {
            'product_commission': total_product_price * Decimal('0.2'),
            'delivery_fees': total_delivery_fees,
            'total_commission': total_commission_amount
        }
        
        # Vendor-wise breakdown - get unique vendors with their stats
        vendor_stats = []
        
        # Use values() to get unique vendors with their aggregated stats
        vendor_aggregates = purchases.values('product__user__id', 'product__user__username').annotate(
            total_transactions=Count('id'),
            total_commission=Sum('agaseke_commission_amount'),
            avg_commission=Avg('agaseke_commission_amount')
        ).order_by('-total_commission')
        
        for vendor_data in vendor_aggregates:
            vendor_stats.append({
                'vendor_id': vendor_data['product__user__id'],
                'vendor_username': vendor_data['product__user__username'],
                'total_transactions': vendor_data['total_transactions'],
                'total_commission': vendor_data['total_commission'] or 0,
                'avg_commission': vendor_data['avg_commission'] or 0
            })
        

        
        # Recent transactions
        recent_transactions = purchases.order_by('-pickup_confirmed_at')[:10]
        
        # Handle export for agaseke
        if export_format in ['csv', 'pdf']:
            if export_format == 'csv':
                headers = ['Vendor', 'Transactions', 'Total Commission', 'Average Commission']
                data = []
                for vendor in vendor_stats:
                    data.append([
                        vendor['vendor_username'],
                        vendor['total_transactions'],
                        f"RWF {vendor['total_commission']:,.1f}",
                        f"RWF {vendor['avg_commission']:,.1f}"
                    ])
                filename = f"agaseke_commission_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return generate_csv_report(data, filename, headers)
            elif export_format == 'pdf':
                headers = ['Vendor', 'Transactions', 'Total Commission', 'Average Commission']
                data = []
                for vendor in vendor_stats:
                    data.append([
                        vendor['vendor_username'],
                        vendor['total_transactions'],
                        f"RWF {vendor['total_commission']:,.1f}",
                        f"RWF {vendor['avg_commission']:,.1f}"
                    ])
                summary_data = {
                    'Total Transactions': total_transactions,
                    'Total Commission': f"RWF {total_commission:,.1f}",
                    'Monthly Commission': f"RWF {monthly_commission:,.1f}",
                    'Commission Rate': '20% + Delivery Fees',
                    'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                filename = f"agaseke_commission_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                title = f"agaseke Commission Report - {request.user.get_full_name() or request.user.username}"
                return generate_pdf_report(data, filename, title, headers, summary_data)
        
        context = {
            'user_type': 'agaseke',
            'total_transactions': total_transactions,
            'total_commission': total_commission,
            'monthly_commission': monthly_commission,
            'monthly_transactions': monthly_purchases.count(),
            'commission_breakdown': commission_breakdown,
            'vendor_stats': vendor_stats,
            'recent_transactions': recent_transactions,
            'commission_rate': 20,  # agaseke gets 20%
            'vendor_rate': 80,      # Vendor gets 80%
        }
        
    else:
        # Regular user - show their purchase history
        purchases = Purchase.objects.filter(
            buyer=request.user,
            status='completed'
        ).select_related('product', 'product__user')
        
        total_spent = purchases.aggregate(
            total=Sum('purchase_price')
        )['total'] or 0
        
        monthly_purchases = purchases.filter(
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        )
        monthly_spent = monthly_purchases.aggregate(
            total=Sum('purchase_price')
        )['total'] or 0
        
        # Handle export for customer
        if export_format in ['csv', 'pdf']:
            headers = ['Product', 'Seller', 'Date', 'Price', 'Status']
            data = []
            for purchase in purchases:
                data.append([
                    purchase.product.title,
                    f"{purchase.product.user.first_name} {purchase.product.user.last_name}",
                    purchase.created_at.strftime('%Y-%m-%d %H:%M'),
                    f"RWF {purchase.purchase_price:,.1f}",
                    purchase.status.title()
                ])
            
            if export_format == 'csv':
                filename = f"customer_purchases_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return generate_csv_report(data, filename, headers)
            elif export_format == 'pdf':
                summary_data = {
                    'Total Purchases': purchases.count(),
                    'Total Spent': f"RWF {total_spent:,.1f}",
                    'Monthly Spent': f"RWF {monthly_spent:,.1f}",
                    'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                filename = f"customer_purchases_{request.user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                title = f"Customer Purchase Report - {request.user.get_full_name() or request.user.username}"
                return generate_pdf_report(data, filename, title, headers, summary_data)
        
        context = {
            'user_type': 'customer',
            'total_purchases': purchases.count(),
            'total_spent': total_spent,
            'monthly_spent': monthly_spent,
            'monthly_purchases': monthly_purchases.count(),
            'recent_transactions': purchases.order_by('-created_at')[:10],
        }
    
    return render(request, 'authentication/sales_statistics.html', context)

@login_required
def vendor_statistics_for_agaseke(request, vendor_id):
    """agaseke users can view detailed statistics for a specific vendor"""
    if not request.user.is_agaseke():
        messages.error(request, 'Access denied. agaseke role required.')
        return redirect('dashboard')
    
    # Get the vendor
    vendor = get_object_or_404(User, id=vendor_id, is_vendor_role=True)
    
    # Get all purchases for this vendor
    purchases = Purchase.objects.filter(
        product__user=vendor,
        status='completed'
    ).select_related('product', 'buyer', 'agaseke_user')
    
    # Calculate vendor statistics (as if agaseke is viewing the vendor's dashboard)
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
    product_stats = purchases.values('product__title').annotate(
        total_sales=Count('id'),
        total_revenue=Sum('vendor_payment_amount'),
        avg_price=Avg('vendor_payment_amount')
    ).order_by('-total_revenue')
    
    # agaseke commission from this vendor
    agaseke_commission = purchases.aggregate(
        total=Sum('agaseke_commission_amount')
    )['total'] or 0
    
    # Monthly agaseke commission
    monthly_agaseke_commission = monthly_purchases.aggregate(
        total=Sum('agaseke_commission_amount')
    )['total'] or 0
    
    # Recent transactions
    recent_transactions = purchases.order_by('-pickup_confirmed_at')[:10]
    
    # Commission breakdown
    total_product_price = purchases.aggregate(total=Sum('purchase_price'))['total'] or 0
    total_delivery_fees = purchases.aggregate(total=Sum('delivery_fee'))['total'] or 0
    
    commission_breakdown = {
        'vendor_earnings': total_revenue,
        'agaseke_commission': agaseke_commission,
        'product_commission': total_product_price * Decimal('0.2'),
        'delivery_fees': total_delivery_fees,
        'total_transaction_value': total_product_price + total_delivery_fees
    }
    
    context = {
        'vendor': vendor,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'monthly_sales': monthly_purchases.count(),
        'product_stats': product_stats,
        'recent_transactions': recent_transactions,
        'agaseke_commission': agaseke_commission,
        'monthly_agaseke_commission': monthly_agaseke_commission,
        'commission_breakdown': commission_breakdown,
        'commission_rate': 80,  # Vendor gets 80%
        'agaseke_rate': 20,   # agaseke gets 20%
    }
    
    return render(request, 'authentication/vendor_statistics_for_agaseke.html', context)
