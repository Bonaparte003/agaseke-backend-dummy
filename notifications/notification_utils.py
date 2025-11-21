"""
Notification utility functions for creating and managing in-app notifications.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def send_notification_to_user(
    user,
    title: str,
    body: str,
    notification_type: str,
    data: Optional[Dict] = None,
    save_to_db: bool = True
) -> Dict:
    """
    Create an in-app notification for a specific user.
    
    Args:
        user: User instance
        title: Notification title
        body: Notification body
        notification_type: Type of notification (from Notification.NOTIFICATION_TYPES)
        data: Optional dictionary of additional data
        save_to_db: Whether to save notification to database
    
    Returns:
        Dictionary with notification instance (if saved)
    """
    from .models import Notification, NotificationPreferences
    
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
    
    # Create in-app notification
    logger.info(f"Creating in-app notification for user {user.username}: {title}")
    
    # Save to database if requested
    notification = None
    if save_to_db:
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {},
        )
        logger.info(f"✓ Notification created successfully (ID: {notification.id})")
    
    return {
        'success': True,
        'notification': notification,
        'message': 'Notification saved to database'
    }


def get_pending_notifications(user) -> Dict:
    """
    Get all pending (unseen) notifications for a user.
    
    Args:
        user: User instance
    
    Returns:
        Dictionary with results: {
            'total_pending': int,
            'notifications': QuerySet
        }
    """
    from .models import Notification
    
    # Get all unseen notifications
    pending_notifications = Notification.objects.filter(
        user=user,
        seen=False
    ).order_by('-created_at')  # Newest first
    
    total_pending = pending_notifications.count()
    
    logger.info(f"User {user.username} has {total_pending} unseen notifications")
    
    return {
        'total_pending': total_pending,
        'notifications': pending_notifications
    }

