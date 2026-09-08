from django.db.models import Count, F, Max, OuterRef, Q, Subquery

from exams.models import ExamAnswer, ExamAttempt, ExamQuestion
from osce.models import OSCEAnswerRecord, OSCEAttempt, OSCEExam, OSCEQuestion

from .models import Badge, StudentBadge


def _recent_badges_for(student):
    """Return the five most recently earned badge types, with award counts."""
    awards = (
        StudentBadge.objects.filter(student=student)
        .values('badge_id')
        .annotate(earned_count=Count('pk'), latest_awarded_at=Max('awarded_at'))
        .order_by('-latest_awarded_at', 'badge_id')[:5]
    )
    badges = {
        badge.pk: badge
        for badge in Badge.objects.filter(pk__in=[award['badge_id'] for award in awards])
    }
    # Preserve the template's small dictionary interface while using the colorized URL.
    return [
        {
            **award,
            'name': badges[award['badge_id']].name,
            'color': badges[award['badge_id']].color,
            'image_url': badges[award['badge_id']].colored_image_url,
        }
        for award in awards
    ]


def _score_summary_for(student, academic_year):
    """Return a student's latest and highest completed, graded attempt."""
    attempts = []

    quiz_attempts = ExamAttempt.objects.filter(
        student=student,
        total_questions__gt=0,
        exam__year=academic_year,
        exam__is_active=True,
        exam__module__is_active=True,
    ).exclude(exam__exam_type='saq')
    attempts.extend(
        {
            'score': round((attempt.score / attempt.total_questions) * 100),
            'submitted_at': attempt.submitted_at,
            'pk': attempt.pk,
        }
        for attempt in quiz_attempts
    )

    osce_attempts = OSCEAttempt.objects.filter(
        student=student,
        total_questions__gt=0,
        exam__year=academic_year,
        exam__is_active=True,
        exam__module__is_active=True,
    )
    for attempt in osce_attempts:
        total_possible = attempt.total_questions + attempt.practical_total
        if total_possible:
            attempts.append({
                'score': round((attempt.mcq_score + attempt.practical_score) / total_possible * 100),
                'submitted_at': attempt.submitted_at,
                'pk': attempt.pk,
            })

    if not attempts:
        return {
            'highest_score': None,
            'highest_score_date': None,
            'latest_score': None,
            'latest_score_date': None,
        }

    latest = max(attempts, key=lambda attempt: (attempt['submitted_at'], attempt['pk']))
    highest = max(attempts, key=lambda attempt: (attempt['score'], attempt['submitted_at'], attempt['pk']))
    return {
        'highest_score': highest['score'],
        'highest_score_date': highest['submitted_at'],
        'latest_score': latest['score'],
        'latest_score_date': latest['submitted_at'],
    }

def recent_badges(request):
    """Provide shared right-panel data for the signed-in student."""
    if not request.user.is_authenticated:
        return {
            'recent_badges': [],
            'highest_score': None,
            'highest_score_date': None,
            'latest_score': None,
            'latest_score_date': None,
            'performance_overview': {
                'correct': 0, 'incorrect': 0, 'unattempted': 0, 'accuracy': 0,
                'correct_percentage': 0, 'answered_percentage': 0,
            },
        }

    academic_year = request.user.academic_year
    if not academic_year:
        return {
            'recent_badges': _recent_badges_for(request.user),
            **_score_summary_for(request.user, academic_year),
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
        **_score_summary_for(request.user, academic_year),
        'performance_overview': performance_overview,
    }
