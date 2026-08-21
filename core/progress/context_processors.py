from django.db.models import Count, F, Max, OuterRef, Q, Subquery

from exams.models import ExamAnswer, ExamAttempt, ExamQuestion
from osce.models import OSCEAnswerRecord, OSCEAttempt, OSCEExam, OSCEQuestion

from .models import StudentBadge


def _recent_badges_for(student):
    """Return the five most recently earned badge types, with award counts."""
    return (
        StudentBadge.objects.filter(student=student)
        .values('badge_id')
        .annotate(
            name=F('badge__name'),
            color=F('badge__color'),
            image_url=F('badge__image_url'),
            earned_count=Count('pk'),
            latest_awarded_at=Max('awarded_at'),
        )
        .order_by('-latest_awarded_at', 'badge_id')[:5]
    )

def recent_badges(request):
    """Provide shared right-panel data for the signed-in student."""
    if not request.user.is_authenticated:
        return {
            'recent_badges': [],
            'performance_overview': {
                'correct': 0, 'incorrect': 0, 'unattempted': 0, 'accuracy': 0,
                'correct_percentage': 0, 'answered_percentage': 0,
            },
        }

    academic_year = request.user.academic_year
    if not academic_year:
        return {
            'recent_badges': _recent_badges_for(request.user),
            'performance_overview': {
                'correct': 0, 'incorrect': 0, 'unattempted': 0, 'accuracy': 0,
                'correct_percentage': 0, 'answered_percentage': 0,
            },
        }

    first_quiz_attempt = ExamAttempt.objects.filter(
        student=request.user,
        total_questions__gt=0,
        exam__year=academic_year,
        exam__is_active=True,
        exam__module__is_active=True,
        exam_id=OuterRef('attempt__exam_id'),
    ).order_by('submitted_at', 'pk').values('pk')[:1]
    quiz_totals = ExamAnswer.objects.filter(
        attempt_id=Subquery(first_quiz_attempt),
    ).exclude(attempt__exam__exam_type='saq').aggregate(
        correct=Count('pk', filter=Q(selected_answer__is_correct=True)),
        incorrect=Count('pk', filter=Q(selected_answer__isnull=False, selected_answer__is_correct=False)),
    )
    first_osce_answer_attempt = OSCEAttempt.objects.filter(
        student=request.user,
        total_questions__gt=0,
        exam__year=academic_year,
        exam__is_active=True,
        exam__module__is_active=True,
        exam_id=OuterRef('attempt__exam_id'),
    ).order_by('submitted_at', 'pk').values('pk')[:1]
    osce_totals = OSCEAnswerRecord.objects.filter(
        attempt_id=Subquery(first_osce_answer_attempt),
    ).aggregate(
        correct=Count('pk', filter=Q(selected_answer__is_correct=True)),
        incorrect=Count('pk', filter=Q(selected_answer__isnull=False, selected_answer__is_correct=False)),
    )
    first_osce_attempt = OSCEAttempt.objects.filter(
        student=request.user,
        total_questions__gt=0,
        exam__year=academic_year,
        exam__is_active=True,
        exam__module__is_active=True,
        exam_id=OuterRef('exam_id'),
    ).order_by('submitted_at', 'pk').values('pk')[:1]
    osce_station_totals = OSCEAttempt.objects.filter(
        pk=Subquery(first_osce_attempt),
        student=request.user,
        practical_total__gt=0,
    ).aggregate(
        correct=Count('pk', filter=Q(practical_score=F('practical_total'))),
        incorrect=Count('pk', filter=~Q(practical_score=F('practical_total'))),
    )
    performance_overview = {
        key: (quiz_totals[key] or 0) + (osce_totals[key] or 0) + (osce_station_totals.get(key) or 0)
        for key in ('correct', 'incorrect')
    }
    available_questions = (
        ExamQuestion.objects.filter(
            exam__year=academic_year,
            exam__is_active=True,
            exam__module__is_active=True,
        ).exclude(exam__exam_type='saq').count()
        + OSCEQuestion.objects.filter(
            exam__year=academic_year,
            exam__is_active=True,
            exam__module__is_active=True,
        ).count()
        + OSCEExam.objects.filter(
            year=academic_year,
            is_active=True,
            module__is_active=True,
        ).exclude(osce_station='none').count()
    )
    performance_overview['unattempted'] = max(
        available_questions - performance_overview['correct'] - performance_overview['incorrect'], 0
    )
    answered = performance_overview['correct'] + performance_overview['incorrect']
    total_questions = answered + performance_overview['unattempted']
    performance_overview['accuracy'] = round((performance_overview['correct'] / answered) * 100) if answered else 0
    performance_overview['correct_percentage'] = round((performance_overview['correct'] / total_questions) * 100, 2) if total_questions else 0
    performance_overview['answered_percentage'] = round((answered / total_questions) * 100, 2) if total_questions else 0

    return {
        'recent_badges': _recent_badges_for(request.user),
        'performance_overview': performance_overview,
    }
