from django.utils import timezone
from django.db.models import F, Q

from .models import UpcomingEvent


def upcoming_events(request):
    """Provide the next events to the shared right-side panel."""
    return {
        'upcoming_events': UpcomingEvent.objects.filter(
            Q(scheduled_at__gte=timezone.now()) | Q(scheduled_at__isnull=True),
        ).order_by(F('scheduled_at').asc(nulls_last=True))[:4],
    }
