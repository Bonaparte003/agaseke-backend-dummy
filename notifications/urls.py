from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Device management
    path('device/register', views.register_device, name='register_device'),
    path('device/delete', views.delete_device, name='delete_device'),
    
    # Notification preferences
    path('preferences', views.notification_preferences, name='preferences'),
    
    # Notification list and management
    path('list', views.list_notifications, name='list_notifications'),
    path('<int:notification_id>/seen', views.mark_notification_seen, name='mark_notification_seen'),
    path('seen-all', views.mark_all_notifications_seen, name='mark_all_notifications_seen'),
    
    # Testing
    path('test', views.test_notification, name='test_notification'),
]

