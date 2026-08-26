from django.contrib import admin

from .models import Notification, NotificationBroadcast
from .services import send_broadcast


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'kind', 'created_at', 'expires_at', 'seen_at')
    list_filter = ('kind', 'seen_at', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    readonly_fields = ('recipient', 'kind', 'title', 'message', 'url', 'image_url', 'created_at', 'expires_at', 'seen_at')

    def has_add_permission(self, request):
        return False


@admin.register(NotificationBroadcast)
class NotificationBroadcastAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'created_by', 'created_at', 'expires_at')
    list_filter = ('target_academic_year', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at', 'created_by')
    fields = ('title', 'message', 'url', 'target_academic_year', 'expires_at', 'created_by', 'created_at')

    @admin.display(description='Audience', ordering='target_academic_year')
    def audience(self, obj):
        return obj.audience_label

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            send_broadcast(obj)
