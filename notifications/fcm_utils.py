"""
FCM (Firebase Cloud Messaging) utility functions for sending push notifications.

To use this module, you need to:
1. Install firebase-admin: pip install firebase-admin
2. Download your Firebase service account JSON file from Firebase Console
3. Set the FCM_CREDENTIALS_FILE path in your settings.py
"""

import logging
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import firebase_admin, but don't fail if it's not installed
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    
    FCM_AVAILABLE = True
    logger.info("firebase-admin package imported successfully")
    
    # Initialize Firebase Admin SDK if credentials are provided
    if hasattr(settings, 'FCM_CREDENTIALS_FILE') and not firebase_admin._apps:
        try:
            import os
            creds_path = settings.FCM_CREDENTIALS_FILE
            
            # Check if credentials file exists
            if not os.path.exists(creds_path):
                logger.error(f"FCM credentials file not found at: {creds_path}")
                logger.error(f"Current working directory: {os.getcwd()}")
                logger.error(f"BASE_DIR would be: {getattr(settings, 'BASE_DIR', 'NOT SET')}")
                FCM_AVAILABLE = False
            else:
                logger.info(f"FCM credentials file found at: {creds_path}")
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
                logger.info("✓ Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
            FCM_AVAILABLE = False
    elif not hasattr(settings, 'FCM_CREDENTIALS_FILE'):
        logger.error("✗ FCM_CREDENTIALS_FILE not set in settings.py. FCM notifications will not be sent.")
        FCM_AVAILABLE = False
    elif firebase_admin._apps:
        logger.info("✓ Firebase Admin SDK already initialized")
        
except ImportError as e:
    FCM_AVAILABLE = False
    logger.error(f"✗ firebase-admin package not installed: {e}")
    logger.error("Install with: pip install firebase-admin")


def send_fcm_notification(
    device_tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict] = None,
    priority: str = 'high'
) -> Dict:
    """
    Send FCM notification to one or more device tokens.
    
    Args:
        device_tokens: List of FCM device tokens
        title: Notification title
        body: Notification body
        data: Optional dictionary of additional data to send with notification
        priority: Notification priority ('high' or 'normal')
    
    Returns:
        Dictionary with results: {
            'success_count': int,
            'failure_count': int,
            'failed_tokens': List[str],
            'responses': List[dict]
        }
    """
    if not FCM_AVAILABLE:
        logger.warning("FCM is not available. Notification not sent.")
        return {
            'success_count': 0,
            'failure_count': len(device_tokens),
            'failed_tokens': device_tokens,
            'error': 'FCM not configured or firebase-admin not installed'
        }
    
    if not device_tokens:
        logger.warning("No device tokens provided")
        return {
            'success_count': 0,
            'failure_count': 0,
            'failed_tokens': [],
            'error': 'No device tokens provided'
        }
    
    # Prepare notification data
    if data is None:
        data = {}
    
    # Convert all data values to strings (FCM requirement)
    data = {k: str(v) for k, v in data.items()}
    
    try:
        # Check if send_multicast is available (firebase-admin >= 6.0.0)
        if hasattr(messaging, 'send_multicast'):
            # Use MulticastMessage for newer versions (more efficient)
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        sound='default',
                        click_action='FLUTTER_NOTIFICATION_CLICK',
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                        ),
                    ),
                ),
                tokens=device_tokens,
            )
            
            # Send the message
            response = messaging.send_multicast(message)
            
            # Process responses
            failed_tokens = []
            responses = []
            
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    failed_tokens.append(device_tokens[idx])
                    error_msg = f"Error: {resp.exception}" if resp.exception else "Unknown error"
                    responses.append({
                        'token': device_tokens[idx],
                        'success': False,
                        'error': error_msg
                    })
                    logger.error(f"Failed to send to {device_tokens[idx]}: {error_msg}")
                else:
                    responses.append({
                        'token': device_tokens[idx],
                        'success': True,
                        'message_id': resp.message_id
                    })
            
            result = {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'failed_tokens': failed_tokens,
                'responses': responses
            }
            
            logger.info(f"FCM notification sent. Success: {response.success_count}, Failed: {response.failure_count}")
            return result
        
        else:
            # Fallback for older firebase-admin versions (< 6.0.0)
            # Send messages individually
            logger.info(f"Using legacy send() method for {len(device_tokens)} tokens (firebase-admin < 6.0.0)")
            
            success_count = 0
            failure_count = 0
            failed_tokens = []
            responses = []
            
            for token in device_tokens:
                try:
                    # Create individual message
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body,
                        ),
                        data=data,
                        android=messaging.AndroidConfig(
                            priority=priority,
                            notification=messaging.AndroidNotification(
                                sound='default',
                                click_action='FLUTTER_NOTIFICATION_CLICK',
                            ),
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    sound='default',
                                    badge=1,
                                ),
                            ),
                        ),
                        token=token,
                    )
                    
                    # Send individual message
                    message_id = messaging.send(message)
                    success_count += 1
                    responses.append({
                        'token': token,
                        'success': True,
                        'message_id': message_id
                    })
                    
                except Exception as e:
                    failure_count += 1
                    failed_tokens.append(token)
                    error_msg = str(e)
                    responses.append({
                        'token': token,
                        'success': False,
                        'error': error_msg
                    })
                    logger.error(f"Failed to send to {token}: {error_msg}")
            
            result = {
                'success_count': success_count,
                'failure_count': failure_count,
                'failed_tokens': failed_tokens,
                'responses': responses
            }
            
            logger.info(f"FCM notification sent (legacy mode). Success: {success_count}, Failed: {failure_count}")
            return result
        
    except Exception as e:
        logger.error(f"Error sending FCM notification: {e}", exc_info=True)
        return {
            'success_count': 0,
            'failure_count': len(device_tokens),
            'failed_tokens': device_tokens,
            'error': str(e)
        }


def send_notification_to_user(
    user,
    title: str,
    body: str,
    notification_type: str,
    data: Optional[Dict] = None,
    save_to_db: bool = True
) -> Dict:
    """
    Send notification to a specific user (all their active devices).
    
    Args:
        user: User instance
        title: Notification title
        body: Notification body
        notification_type: Type of notification (from Notification.NOTIFICATION_TYPES)
        data: Optional dictionary of additional data
        save_to_db: Whether to save notification to database
    
    Returns:
        Dictionary with FCM send results and notification instance (if saved)
    """
    from .models import FCMDevice, Notification, NotificationPreferences
    
    # Check if user has notifications enabled
    try:
        prefs = NotificationPreferences.objects.get(user=user)
        if not prefs.notifications_enabled:
            logger.info(f"Notifications disabled for user {user.username}")
            return {
                'success': False,
                'error': 'Notifications disabled by user'
            }
    except NotificationPreferences.DoesNotExist:
        # Create default preferences if they don't exist
        prefs = NotificationPreferences.objects.create(user=user)
    
    # Get active device tokens for this user
    devices = FCMDevice.objects.filter(user=user, is_active=True)
    device_tokens = list(devices.values_list('device_token', flat=True))
    
    if not device_tokens:
        logger.info(f"No active devices found for user {user.username}")
    
    # Send FCM notification
    fcm_result = send_fcm_notification(
        device_tokens=device_tokens,
        title=title,
        body=body,
        data=data or {}
    )
    
    # Save to database if requested
    notification = None
    if save_to_db:
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {},
            already_sent=True,  # Mark as sent to prevent duplicates
            fcm_sent=len(device_tokens) > 0,
            fcm_success=fcm_result.get('success_count', 0) > 0,
            fcm_error=fcm_result.get('error', '') if fcm_result.get('failure_count', 0) > 0 else None
        )
    
    return {
        'fcm_result': fcm_result,
        'notification': notification,
        'device_count': len(device_tokens)
    }


def remove_invalid_tokens(failed_tokens: List[str]):
    """
    Remove invalid/expired FCM tokens from the database.
    
    Args:
        failed_tokens: List of FCM tokens that failed to receive notifications
    """
    from .models import FCMDevice
    
    if not failed_tokens:
        return
    
    # Mark failed tokens as inactive
    updated_count = FCMDevice.objects.filter(
        device_token__in=failed_tokens
    ).update(is_active=False)
    
    logger.info(f"Marked {updated_count} invalid FCM tokens as inactive")


def resend_pending_notifications(user) -> Dict:
    """
    Resend all pending notifications that failed to send via FCM.
    This is typically called when a device is newly registered or comes back online.
    
    Args:
        user: User instance
    
    Returns:
        Dictionary with results: {
            'total_pending': int,
            'attempted': int,
            'success_count': int,
            'failure_count': int
        }
    """
    from .models import Notification, FCMDevice
    
    # Get all notifications that haven't been successfully sent via FCM
    pending_notifications = Notification.objects.filter(
        user=user,
        fcm_success=False
    ).order_by('created_at')  # Oldest first
    
    total_pending = pending_notifications.count()
    
    if total_pending == 0:
        logger.info(f"No pending notifications for user {user.username}")
        return {
            'total_pending': 0,
            'attempted': 0,
            'success_count': 0,
            'failure_count': 0
        }
    
    # Get active device tokens for this user
    devices = FCMDevice.objects.filter(user=user, is_active=True)
    device_tokens = list(devices.values_list('device_token', flat=True))
    
    if not device_tokens:
        logger.info(f"No active devices found for user {user.username}, cannot resend")
        return {
            'total_pending': total_pending,
            'attempted': 0,
            'success_count': 0,
            'failure_count': 0,
            'error': 'No active devices'
        }
    
    success_count = 0
    failure_count = 0
    
    # Resend each notification
    for notification in pending_notifications:
        try:
            # Send FCM notification
            fcm_result = send_fcm_notification(
                device_tokens=device_tokens,
                title=notification.title,
                body=notification.body,
                data=notification.data
            )
            
            # Update notification status
            notification.fcm_sent = True
            notification.fcm_success = fcm_result.get('success_count', 0) > 0
            
            if fcm_result.get('failure_count', 0) > 0:
                notification.fcm_error = fcm_result.get('error', 'Failed to send to some devices')
                failure_count += 1
            else:
                notification.fcm_error = None
                success_count += 1
            
            notification.save(update_fields=['fcm_sent', 'fcm_success', 'fcm_error'])
            
        except Exception as e:
            logger.error(f"Error resending notification {notification.id}: {e}")
            notification.fcm_error = str(e)
            notification.save(update_fields=['fcm_error'])
            failure_count += 1
    
    logger.info(f"Resent {total_pending} notifications for user {user.username}. Success: {success_count}, Failed: {failure_count}")
    
    return {
        'total_pending': total_pending,
        'attempted': total_pending,
        'success_count': success_count,
        'failure_count': failure_count
    }


def test_fcm_notification(device_token: str) -> Dict:
    """
    Send a test notification to verify FCM is working.
    
    Args:
        device_token: FCM device token to test
    
    Returns:
        Dictionary with test results
    """
    return send_fcm_notification(
        device_tokens=[device_token],
        title="Test Notification",
        body="This is a test notification from Agaseke",
        data={'test': 'true'}
    )

