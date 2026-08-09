from django.utils import timezone

from .models import UpcomingEvent


def upcoming_events(request):
    """Provide the next events to the shared right-side panel."""
    return {
        'upcoming_events': UpcomingEvent.objects.filter(
            scheduled_at__gte=timezone.now(),
        )[:4],
    }
