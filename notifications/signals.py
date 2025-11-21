"""
Signals for automatically sending notifications when purchase events occur.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from products.models import Purchase
from .notification_utils import send_notification_to_user
from .models import NotificationPreferences
import logging

logger = logging.getLogger(__name__)


def should_send_notification(user, notification_type):
    """
    Check if user has enabled notifications for this type.
    
    Args:
        user: User instance
        notification_type: Type of notification to check
    
    Returns:
        Boolean indicating whether to send notification
    """
    try:
        prefs = NotificationPreferences.objects.get(user=user)
        
        # Check master toggle first
        if not prefs.notifications_enabled:
            return False
        
        # Check specific notification type
        notification_map = {
            'purchase_created': prefs.purchase_created_enabled,
            'purchase_pending': prefs.purchase_status_changed_enabled,
            'purchase_processing': prefs.purchase_status_changed_enabled,
            'purchase_awaiting_pickup': prefs.purchase_status_changed_enabled,
            'purchase_awaiting_delivery': prefs.purchase_status_changed_enabled,
            'purchase_out_for_delivery': prefs.purchase_status_changed_enabled,
            'purchase_completed': prefs.purchase_completed_enabled,
            'purchase_cancelled': prefs.purchase_status_changed_enabled,
            'product_purchased': prefs.product_purchased_enabled,
            'product_purchase_completed': prefs.product_purchase_completed_enabled,
        }
        
        return notification_map.get(notification_type, True)
        
    except NotificationPreferences.DoesNotExist:
        # If preferences don't exist, allow notifications (default behavior)
        return True


@receiver(post_save, sender=Purchase)
def notify_on_purchase_created(sender, instance, created, **kwargs):
    """
    Send notifications when a new purchase is created.
    
    Notifications sent:
    1. To buyer: Purchase confirmation
    2. To vendor: New product purchase
    """
    if not created:
        return  # Only trigger on creation, not updates
    
    purchase = instance
    buyer = purchase.buyer
    vendor = purchase.product.user  # Assuming Post model has a 'user' field for vendor
    
    try:
        # 1. Notify buyer about purchase confirmation
        if should_send_notification(buyer, 'purchase_created'):
            send_notification_to_user(
                user=buyer,
                title="Purchase Confirmed! 🎉",
                body=f"Your order #{purchase.order_id} for {purchase.product.title} has been confirmed.",
                notification_type='purchase_created',
                data={
                    'purchase_id': str(purchase.id),
                    'order_id': purchase.order_id,
                    'product_id': str(purchase.product.id),
                    'status': purchase.status,
                    'type': 'purchase_created'
                },
                save_to_db=True
            )
            logger.info(f"Sent purchase confirmation notification to buyer {buyer.username}")
        
        # 2. Notify vendor about new purchase (only if not completed yet)
        if purchase.status != 'completed' and should_send_notification(vendor, 'product_purchased'):
            send_notification_to_user(
                user=vendor,
                title="New Product Purchase! 🛍️",
                body=f"Your product '{purchase.product.title}' has been purchased (Order #{purchase.order_id}).",
                notification_type='product_purchased',
                data={
                    'purchase_id': str(purchase.id),
                    'order_id': purchase.order_id,
                    'product_id': str(purchase.product.id),
                    'status': purchase.status,
                    'buyer_username': buyer.username,
                    'type': 'product_purchased'
                },
                save_to_db=True
            )
            logger.info(f"Sent new purchase notification to vendor {vendor.username}")
            
    except Exception as e:
        logger.error(f"Error sending purchase creation notifications: {e}", exc_info=True)


# Store previous status to detect changes
_purchase_previous_status = {}

@receiver(pre_save, sender=Purchase)
def store_previous_status(sender, instance, **kwargs):
    """Store the previous status before save to detect changes."""
    if instance.pk:  # Only for existing instances
        try:
            old_instance = Purchase.objects.get(pk=instance.pk)
            _purchase_previous_status[instance.pk] = old_instance.status
        except Purchase.DoesNotExist:
            pass


@receiver(post_save, sender=Purchase)
def notify_on_purchase_status_changed(sender, instance, created, **kwargs):
    """
    Send notifications when purchase status changes.
    
    Notifications sent based on status:
    - When status changes to 'completed':
      * To buyer: Purchase completed
      * To vendor: Purchase completed
    - When status changes to other statuses:
      * To buyer: Status update
    """
    if created:
        return  # Already handled by notify_on_purchase_created
    
    purchase = instance
    buyer = purchase.buyer
    vendor = purchase.product.user
    
    # Get previous status
    previous_status = _purchase_previous_status.get(purchase.pk)
    
    # Clear stored status
    if purchase.pk in _purchase_previous_status:
        del _purchase_previous_status[purchase.pk]
    
    # If status hasn't changed, don't send notifications
    if previous_status == purchase.status:
        return
    
    try:
        # Map status to user-friendly messages
        status_messages = {
            'pending': {
                'title': 'Order Pending',
                'body': f"Your order #{purchase.order_id} is pending confirmation."
            },
            'processing': {
                'title': 'Order Processing ⚙️',
                'body': f"Your order #{purchase.order_id} is being processed."
            },
            'awaiting_pickup': {
                'title': 'Ready for Pickup 📦',
                'body': f"Your order #{purchase.order_id} is ready for pickup at Agaseke."
            },
            'awaiting_delivery': {
                'title': 'Ready for Delivery 🚚',
                'body': f"Your order #{purchase.order_id} is ready for delivery."
            },
            'out_for_delivery': {
                'title': 'Out for Delivery 🚚',
                'body': f"Your order #{purchase.order_id} is out for delivery."
            },
            'completed': {
                'title': 'Order Completed ✅',
                'body': f"Your order #{purchase.order_id} has been completed. Thank you for shopping with Agaseke!"
            },
            'cancelled': {
                'title': 'Order Cancelled ❌',
                'body': f"Your order #{purchase.order_id} has been cancelled."
            }
        }
        
        # Get notification type based on status
        notification_type = f"purchase_{purchase.status}"
        
        # 1. Notify buyer about status change
        if purchase.status in status_messages and should_send_notification(buyer, notification_type):
            message = status_messages[purchase.status]
            send_notification_to_user(
                user=buyer,
                title=message['title'],
                body=message['body'],
                notification_type=notification_type,
                data={
                    'purchase_id': str(purchase.id),
                    'order_id': purchase.order_id,
                    'product_id': str(purchase.product.id),
                    'status': purchase.status,
                    'previous_status': previous_status or 'unknown',
                    'type': 'status_change'
                },
                save_to_db=True
            )
            logger.info(f"Sent status change notification to buyer {buyer.username}: {previous_status} -> {purchase.status}")
        
        # 2. If status changed to 'completed', notify vendor
        if purchase.status == 'completed' and should_send_notification(vendor, 'product_purchase_completed'):
            send_notification_to_user(
                user=vendor,
                title="Purchase Completed! 🎉",
                body=f"Purchase of your product '{purchase.product.title}' (Order #{purchase.order_id}) has been completed.",
                notification_type='product_purchase_completed',
                data={
                    'purchase_id': str(purchase.id),
                    'order_id': purchase.order_id,
                    'product_id': str(purchase.product.id),
                    'status': purchase.status,
                    'buyer_username': buyer.username,
                    'type': 'purchase_completed'
                },
                save_to_db=True
            )
            logger.info(f"Sent purchase completed notification to vendor {vendor.username}")
            
    except Exception as e:
        logger.error(f"Error sending status change notifications: {e}", exc_info=True)

