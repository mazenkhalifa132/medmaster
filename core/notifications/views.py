from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
@require_POST
def mark_all_seen(request):
    Notification.objects.filter(
        recipient=request.user,
        seen_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).update(seen_at=timezone.now())
    return JsonResponse({'seen': True})


@login_required
@require_POST
def dismiss(request, notification_id):
    updated = Notification.objects.filter(
        pk=notification_id,
        recipient=request.user,
        dismissed_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).update(dismissed_at=timezone.now())
    return JsonResponse({'dismissed': bool(updated)})

# Create your views here.
