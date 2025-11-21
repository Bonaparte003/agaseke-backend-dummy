from django.contrib import admin
from .models import Notification, NotificationPreferences


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'seen', 'created_at']
    list_filter = ['notification_type', 'seen', 'created_at']
    search_fields = ['user__username', 'user__email', 'title', 'body']
    readonly_fields = ['created_at', 'seen_at']
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('user', 'notification_type', 'title', 'body', 'purchase')
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
