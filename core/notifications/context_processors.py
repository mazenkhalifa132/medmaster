from django.utils import timezone

from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {'active_notifications': [], 'active_notification_count': 0}
    active = Notification.objects.filter(
        recipient=request.user,
        dismissed_at__isnull=True,
        expires_at__gt=timezone.now(),
    )
    return {
        'active_notifications': active,
        'active_notification_count': active.count(),
    }
