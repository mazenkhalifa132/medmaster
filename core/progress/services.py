from datetime import timedelta

from django.db import transaction
from django.db import models
from django.db.models import F
from django.utils import timezone

from exams.models import ExamAttempt
from osce.models import OSCEAttempt

from .models import (
    Badge, DailyActivity, PointTransaction, StudentBadge, StudentProgress,
    StudentWeeklyGoal, WeeklyGoal,
)


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
            evaluate_weekly_goals(student=student)
    return created


def _award_badge(*, student, badge, source_key):
    """Award a badge and its XP once for each unique qualifying event."""
    with transaction.atomic():
        award, created = StudentBadge.objects.get_or_create(
            student=student,
            badge=badge,
            source_key=source_key,
        )
        if created and badge.xp_reward:
            PointTransaction.objects.create(
                student=student,
                source_key=f'badge-award:{award.pk}',
                source_label=f'Badge earned: {badge.name}',
                points=badge.xp_reward,
                is_correct=False,
            )
            StudentProgress.objects.get_or_create(student=student)
            StudentProgress.objects.filter(student=student).update(total_points=F('total_points') + badge.xp_reward)
    return award, created


def award_exam_badges(*, student, score, total_questions, attempt_key):
    """Award all score-based badges earned by a completed exam or OSCE."""
    if not total_questions:
        return []
    percentage = (score / total_questions) * 100
    badges = Badge.objects.filter(
        is_active=True,
        rule_type=Badge.EXAM_SCORE,
        threshold__lte=percentage,
    )
    return [
        _award_badge(student=student, badge=badge, source_key=f'badge:{attempt_key}:{badge.pk}')[0]
        for badge in badges
    ]


def record_daily_activity(*, student):
    """Register today's dashboard visit and award any qualifying streak badges."""
    today = timezone.localdate()
    activity, _ = DailyActivity.objects.get_or_create(student=student, date=today)

    activity_dates = set(DailyActivity.objects.filter(student=student).values_list('date', flat=True))
    streak = 0
    day = today
    while day in activity_dates:
        streak += 1
        day -= timedelta(days=1)

    badges = Badge.objects.filter(
        is_active=True,
        rule_type=Badge.LOGIN_STREAK,
        threshold__lte=streak,
    )
    for badge in badges:
        _award_badge(student=student, badge=badge, source_key=f'badge:streak:{activity.pk}:{badge.pk}')
    return streak


def weekly_goal_progress(*, student, goal, today=None):
    """Return a student's progress and completion state for one goal."""
    today = today or timezone.localdate()
    first_exam_attempt_ids = {}
    for attempt in ExamAttempt.objects.filter(
        student=student,
        total_questions__gt=0,
    ).order_by('exam_id', 'submitted_at', 'pk'):
        first_exam_attempt_ids.setdefault(attempt.exam_id, attempt.pk)

    first_osce_attempt_ids = {}
    for attempt in OSCEAttempt.objects.filter(
        student=student,
        total_questions__gt=0,
    ).order_by('exam_id', 'submitted_at', 'pk'):
        first_osce_attempt_ids.setdefault(attempt.exam_id, attempt.pk)

    first_attempt_filters = models.Q(pk__in=[])
    for attempt_id in first_exam_attempt_ids.values():
        first_attempt_filters |= models.Q(source_key__startswith=f'exam-answer:{attempt_id}:')
    for attempt_id in first_osce_attempt_ids.values():
        first_attempt_filters |= models.Q(source_key__startswith=f'osce-mcq:{attempt_id}:')

    answer_transactions = PointTransaction.objects.filter(
        student=student,
        created_at__date__gte=goal.start_date,
        created_at__date__lt=goal.end_date,
    ).filter(first_attempt_filters)
    if goal.goal_type == WeeklyGoal.QUESTIONS_SOLVED:
        current = answer_transactions.count()
        completed = current >= goal.target
    elif goal.goal_type == WeeklyGoal.CORRECT_ANSWERS:
        current = answer_transactions.filter(is_correct=True).count()
        completed = current >= goal.target
    else:
        current = answer_transactions.filter(is_correct=False).count()
        completed = today >= goal.end_date and current <= goal.target

    return {
        'current': current,
        'completed': completed,
        'failed': goal.goal_type == WeeklyGoal.MAX_INCORRECT_ANSWERS and current > goal.target,
        'has_ended': today >= goal.end_date,
    }


def evaluate_weekly_goals(*, student, today=None):
    """Award each earned active weekly goal once and return its progress."""
    today = today or timezone.localdate()
    goal_progress = []
    for goal in WeeklyGoal.objects.filter(is_active=True, start_date__lte=today):
        progress = weekly_goal_progress(student=student, goal=goal, today=today)
        if progress['completed']:
            with transaction.atomic():
                _, created = StudentWeeklyGoal.objects.get_or_create(student=student, goal=goal)
                if created and goal.xp_reward:
                    PointTransaction.objects.create(
                        student=student,
                        source_key=f'weekly-goal:{goal.pk}:{student.pk}',
                        source_label=f'Weekly goal completed: {goal.name}',
                        points=goal.xp_reward,
                        is_correct=False,
                    )
                    StudentProgress.objects.get_or_create(student=student)
                    StudentProgress.objects.filter(student=student).update(
                        total_points=F('total_points') + goal.xp_reward
                    )
            progress['awarded'] = StudentWeeklyGoal.objects.filter(student=student, goal=goal).exists()
        else:
            progress['awarded'] = False
        goal_progress.append((goal, progress))
    return goal_progress
