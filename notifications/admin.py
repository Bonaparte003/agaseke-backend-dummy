from django.contrib import admin
from .models import FCMDevice, Notification, NotificationPreferences


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'device_token_short', 'is_active', 'created_at']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'device_token', 'device_id']
    readonly_fields = ['created_at', 'updated_at']
    
    def device_token_short(self, obj):
        """Display truncated device token for readability"""
        return f"{obj.device_token[:30]}..." if len(obj.device_token) > 30 else obj.device_token
    device_token_short.short_description = 'Device Token'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'seen', 'already_sent', 'fcm_success', 'created_at']
    list_filter = ['notification_type', 'seen', 'already_sent', 'fcm_sent', 'fcm_success', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'body']
    readonly_fields = ['created_at', 'seen_at']
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'notification_type', 'title', 'body', 'purchase')
        }),
        ('FCM Delivery', {
            'fields': ('already_sent', 'fcm_sent', 'fcm_success', 'fcm_error')
        }),
        ('Seen Status', {
            'fields': ('seen', 'seen_at')
        }),
        ('Additional Data', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def mark_as_seen(self, request, queryset):
        """Admin action to mark selected notifications as seen"""
        count = 0
        for notification in queryset:
            if not notification.seen:
                notification.mark_as_seen()
                count += 1
        self.message_user(request, f"{count} notification(s) marked as seen.")
    mark_as_seen.short_description = "Mark selected notifications as seen"
    
    actions = ['mark_as_seen']


@admin.register(NotificationPreferences)
class NotificationPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'notifications_enabled', 'purchase_completed_enabled', 
                    'product_purchased_enabled', 'created_at']
    list_filter = ['notifications_enabled', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('General Settings', {
            'fields': ('notifications_enabled',)
        }),
        ('Buyer Notifications', {
            'fields': ('purchase_created_enabled', 'purchase_status_changed_enabled', 
                      'purchase_completed_enabled')
        }),
        ('Vendor Notifications', {
            'fields': ('product_purchased_enabled', 'product_purchase_completed_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
