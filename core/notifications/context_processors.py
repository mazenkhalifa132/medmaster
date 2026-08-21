from django.utils import timezone

from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {'unread_notifications': [], 'unread_notification_count': 0}
    unread = Notification.objects.filter(
        recipient=request.user,
        seen_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    return {
        'unread_notifications': unread[:10],
        'unread_notification_count': unread.count(),
    }
