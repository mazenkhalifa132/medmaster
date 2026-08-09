from django.db import transaction
from django.db.models import F

from .models import PointTransaction, StudentProgress


CORRECT_POINTS = 2
INCORRECT_POINTS = -1


def record_answer_points(*, student, source_key, source_label, is_correct):
    """Record +2/-1 exactly once for a scored question or OSCE station."""
    points = CORRECT_POINTS if is_correct else INCORRECT_POINTS
    with transaction.atomic():
        _, created = PointTransaction.objects.get_or_create(
            source_key=source_key,
            defaults={
                'student': student,
                'source_label': source_label,
                'points': points,
                'is_correct': is_correct,
            },
        )
        if created:
            StudentProgress.objects.get_or_create(student=student)
            StudentProgress.objects.filter(student=student).update(
                total_points=F('total_points') + points,
                correct_answers=F('correct_answers') + (1 if is_correct else 0),
                incorrect_answers=F('incorrect_answers') + (0 if is_correct else 1),
            )
    return created
