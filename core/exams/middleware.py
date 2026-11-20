from django.utils import timezone

from .models import Exam, ExamActivationAnnouncement
from .telegram import send_exam_activation_announcement


class ScheduledExamActivationMiddleware:
    """Activate scheduled exams on the first request on or after their date."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        activated_ids = list(Exam.objects.filter(
            auto_activate=True,
            activation_date__lte=timezone.localdate(),
            is_active=False,
        ).values_list('pk', flat=True))
        if activated_ids:
            Exam.objects.filter(pk__in=activated_ids).update(is_active=True)
            for exam_id in activated_ids:
                send_exam_activation_announcement(exam_id)

        pending_ids = ExamActivationAnnouncement.objects.filter(
            sent_at__isnull=True, exam__is_active=True,
        ).values_list('exam_id', flat=True)
        for exam_id in pending_ids:
            send_exam_activation_announcement(exam_id)
        return self.get_response(request)
