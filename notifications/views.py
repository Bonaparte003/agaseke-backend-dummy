from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
import json
import logging

from .models import FCMDevice, Notification, NotificationPreferences
from .fcm_utils import send_notification_to_user, test_fcm_notification, resend_pending_notifications
from authentication.decorators import jwt_required

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def register_device(request):
    """
    Register or update an FCM device token for push notifications.
    
    Request body (JSON):
    {
        "device_token": "string (required)",
        "device_id": "string (optional)",
        "device_type": "android|ios|web (optional, default: android)",
        "notification_enabled": true|false (optional, default: true)
    }
    """
    try:
        data = json.loads(request.body)
        device_token = data.get('device_token')
        device_id = data.get('device_id', '')
        device_type = data.get('device_type', 'android')
        notification_enabled = data.get('notification_enabled', True)
        
        if not device_token:
            return JsonResponse({
                'success': False,
                'error': 'device_token is required'
            }, status=400)
        
        # Validate device_type
        valid_device_types = ['android', 'ios', 'web']
        if device_type not in valid_device_types:
            return JsonResponse({
                'success': False,
                'error': f'device_type must be one of: {", ".join(valid_device_types)}'
            }, status=400)
        
        user = request.user
        
        with transaction.atomic():
            # Check if device token already exists
            device, created = FCMDevice.objects.update_or_create(
                device_token=device_token,
                defaults={
                    'user': user,
                    'device_id': device_id,
                    'device_type': device_type,
                    'is_active': True
                }
            )
            
            # Update notification preferences if provided
            prefs, _ = NotificationPreferences.objects.get_or_create(user=user)
            if not notification_enabled and prefs.notifications_enabled:
                prefs.notifications_enabled = False
                prefs.save()
            elif notification_enabled and not prefs.notifications_enabled:
                prefs.notifications_enabled = True
                prefs.save()
        
        # Resend any pending notifications that failed previously
        pending_result = None
        try:
            pending_result = resend_pending_notifications(user)
            if pending_result['success_count'] > 0:
                logger.info(f"Successfully resent {pending_result['success_count']} pending notifications to {user.username}")
        except Exception as e:
            logger.error(f"Error resending pending notifications: {e}", exc_info=True)
        
        response_data = {
            'success': True,
            'message': 'Device registered successfully' if created else 'Device updated successfully',
            'device': {
                'id': device.id,
                'device_token': device.device_token[:20] + '...',  # Truncate for security
                'device_type': device.device_type,
                'is_active': device.is_active,
                'created_at': device.created_at.isoformat()
            },
            'notification_enabled': prefs.notifications_enabled
        }
        
        # Include pending notifications info if any were resent
        if pending_result and pending_result['attempted'] > 0:
            response_data['pending_notifications'] = {
                'total': pending_result['total_pending'],
                'resent': pending_result['success_count'],
                'failed': pending_result['failure_count']
            }
        
        return JsonResponse(response_data, status=201 if created else 200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error registering device: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def delete_device(request):
    """
    Delete/unregister an FCM device token (on logout).
    
    Request body (JSON):
    {
        "device_token": "string (required)"
    }
    
    Or delete all devices for the user:
    {
        "delete_all": true
    }
    """
    try:
        data = json.loads(request.body)
        device_token = data.get('device_token')
        delete_all = data.get('delete_all', False)
        
        user = request.user
        
        if delete_all:
            # Delete all devices for this user
            deleted_count, _ = FCMDevice.objects.filter(user=user).delete()
            return JsonResponse({
                'success': True,
                'message': f'Deleted {deleted_count} device(s)',
                'deleted_count': deleted_count
            })
        
        if not device_token:
            return JsonResponse({
                'success': False,
                'error': 'device_token is required (or set delete_all=true)'
            }, status=400)
        
        # Delete specific device
        deleted_count, _ = FCMDevice.objects.filter(
            user=user,
            device_token=device_token
        ).delete()
        
        if deleted_count > 0:
            return JsonResponse({
                'success': True,
                'message': 'Device deleted successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Device not found'
            }, status=404)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error deleting device: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
@jwt_required
def notification_preferences(request):
    """
    Get or update notification preferences for the authenticated user.
    
    GET: Returns current notification preferences
    POST: Updates notification preferences
    
    Request body for POST (JSON):
    {
        "notifications_enabled": true|false,
        "purchase_created_enabled": true|false,
        "purchase_status_changed_enabled": true|false,
        "purchase_completed_enabled": true|false,
        "product_purchased_enabled": true|false,
        "product_purchase_completed_enabled": true|false
    }
    """
    user = request.user
    
    try:
        # Get or create preferences
        prefs, created = NotificationPreferences.objects.get_or_create(user=user)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'preferences': {
                    'notifications_enabled': prefs.notifications_enabled,
                    'purchase_created_enabled': prefs.purchase_created_enabled,
                    'purchase_status_changed_enabled': prefs.purchase_status_changed_enabled,
                    'purchase_completed_enabled': prefs.purchase_completed_enabled,
                    'product_purchased_enabled': prefs.product_purchased_enabled,
                    'product_purchase_completed_enabled': prefs.product_purchase_completed_enabled,
                }
            })
        
        # POST: Update preferences
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'notifications_enabled' in data:
            prefs.notifications_enabled = bool(data['notifications_enabled'])
        if 'purchase_created_enabled' in data:
            prefs.purchase_created_enabled = bool(data['purchase_created_enabled'])
        if 'purchase_status_changed_enabled' in data:
            prefs.purchase_status_changed_enabled = bool(data['purchase_status_changed_enabled'])
        if 'purchase_completed_enabled' in data:
            prefs.purchase_completed_enabled = bool(data['purchase_completed_enabled'])
        if 'product_purchased_enabled' in data:
            prefs.product_purchased_enabled = bool(data['product_purchased_enabled'])
        if 'product_purchase_completed_enabled' in data:
            prefs.product_purchase_completed_enabled = bool(data['product_purchase_completed_enabled'])
        
        prefs.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification preferences updated successfully',
            'preferences': {
                'notifications_enabled': prefs.notifications_enabled,
                'purchase_created_enabled': prefs.purchase_created_enabled,
                'purchase_status_changed_enabled': prefs.purchase_status_changed_enabled,
                'purchase_completed_enabled': prefs.purchase_completed_enabled,
                'product_purchased_enabled': prefs.product_purchased_enabled,
                'product_purchase_completed_enabled': prefs.product_purchase_completed_enabled,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error managing notification preferences: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def list_notifications(request):
    """
    Get list of notifications for the authenticated user.
    
    Query parameters:
    - limit: Number of notifications to return (default: 20)
    - offset: Offset for pagination (default: 0)
    - unseen_only: Return only unseen notifications (default: false)
    """
    user = request.user
    
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        unseen_only = request.GET.get('unseen_only', 'false').lower() == 'true'
        
        # Query notifications
        notifications = Notification.objects.filter(user=user)
        
        if unseen_only:
            notifications = notifications.filter(seen=False)
        
        # Get total count and stats
        total_count = notifications.count()
        unseen_count = Notification.objects.filter(user=user, seen=False).count()
        
        # Apply pagination
        notifications = notifications[offset:offset + limit]
        
        # Serialize notifications
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                'id': notif.id,
                'type': notif.notification_type,
                'title': notif.title,
                'body': notif.body,
                'seen': notif.seen,
                'seen_at': notif.seen_at.isoformat() if notif.seen_at else None,
                'created_at': notif.created_at.isoformat(),
                'data': notif.data,
                'purchase_id': notif.purchase.id if notif.purchase else None,
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'total_count': total_count,
            'unseen_count': unseen_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error listing notifications: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def mark_notification_seen(request, notification_id):
    """
    Mark a specific notification as seen (viewed in list).
    """
    user = request.user
    
    try:
        notification = Notification.objects.get(id=notification_id, user=user)
        notification.mark_as_seen()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as seen'
        })
        
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Notification not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error marking notification as seen: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def mark_all_notifications_seen(request):
    """
    Mark all notifications as seen for the authenticated user.
    """
    user = request.user
    
    try:
        from django.utils import timezone
        updated_count = Notification.objects.filter(
            user=user,
            seen=False
        ).update(
            seen=True,
            seen_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Marked {updated_count} notification(s) as seen',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error marking all notifications as seen: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def test_notification(request):
    """
    Send a test notification to the authenticated user (for testing purposes).
    Only available in DEBUG mode.
    """
    from django.conf import settings
    
    if not settings.DEBUG:
        return JsonResponse({
            'success': False,
            'error': 'Test notifications are only available in DEBUG mode'
        }, status=403)
    
    user = request.user
    
    try:
        result = send_notification_to_user(
            user=user,
            title="Test Notification",
            body="This is a test notification from Agaseke",
            notification_type="purchase_created",
            data={'test': 'true'},
            save_to_db=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Test notification sent',
            'result': {
                'device_count': result['device_count'],
                'fcm_success_count': result['fcm_result'].get('success_count', 0),
                'fcm_failure_count': result['fcm_result'].get('failure_count', 0),
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
