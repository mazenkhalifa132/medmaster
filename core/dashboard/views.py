from django.contrib.auth.decorators import login_required
from datetime import timedelta

from django.db.models import Count, F, Max, Q, Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from exams.models import Exam, ExamAttempt
from dashboard.models import TelegramGroup
from modules.models import Module
from notes.models import Note
from osce.models import OSCEAttempt, OSCEExam
from progress.models import Badge, PointTransaction, StudentBadge, StudentProgress, WeeklyGoal
from progress.services import evaluate_weekly_goals, record_daily_activity
from verification.services import can_access_content

import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse


@login_required(login_url='auth')
def home(request):
    day_streak = record_daily_activity(student=request.user)
    today = timezone.localdate()
    weekly_goal_results = dict(evaluate_weekly_goals(student=request.user, today=today))
    student_progress, _ = StudentProgress.objects.get_or_create(student=request.user)
    rank = student_progress.rank
    rank_span = rank.max_points - rank.min_points if rank else 0
    rank_percent = min(max(((max(student_progress.total_points, 0) - rank.min_points) / rank_span) * 100, 0), 100) if rank_span else 0
    weekly_goal = WeeklyGoal.objects.filter(
        is_active=True,
        start_date__lte=today,
        start_date__gt=today - timedelta(days=7),
    ).order_by('-start_date', '-pk').first()
    weekly_goal_data = None
    if weekly_goal and today < weekly_goal.end_date:
        weekly_goal_data = weekly_goal_results.get(weekly_goal)
        if weekly_goal_data:
            weekly_goal_data['goal'] = weekly_goal
            weekly_goal_data['days_remaining'] = (weekly_goal.end_date - today).days
            weekly_goal_data['percent'] = min(
                round((weekly_goal_data['current'] / weekly_goal.target) * 100) if weekly_goal.target else 100,
                100,
            )
    week_start = today - timedelta(days=today.weekday())
    questions_solved_this_week = PointTransaction.objects.filter(
        student=request.user,
        created_at__date__gte=week_start,
    ).filter(
        Q(source_key__startswith='exam-answer:') | Q(source_key__startswith='osce-mcq:')
    ).count()
    weekly_xp_by_date = {
        row['created_at__date']: row['points'] or 0
        for row in PointTransaction.objects.filter(
            student=request.user,
            created_at__date__gte=week_start,
            created_at__date__lte=today,
        ).values('created_at__date').annotate(points=Sum('points'))
    }
    weekly_xp_total = sum(weekly_xp_by_date.values())
    running_xp = student_progress.total_points - weekly_xp_total
    xp_chart_data = []
    for offset in range(7):
        date = week_start + timedelta(days=offset)
        running_xp += weekly_xp_by_date.get(date, 0)
        xp_chart_data.append({
            'label': f'{date:%b} {date.day}',
            'xp': running_xp,
            'is_future': date > today,
        })
    badges_earned = StudentBadge.objects.filter(student=request.user)
    badges_earned_today = badges_earned.filter(awarded_at__date=today).count()

    def score_totals_between(start_date=None, end_date=None):
        date_filters = {}
        if start_date:
            date_filters['submitted_at__date__gte'] = start_date
        if end_date:
            date_filters['submitted_at__date__lt'] = end_date
        exam_totals = request.user.exam_attempts.filter(total_questions__gt=0, **date_filters).aggregate(
            score=Sum('score'), total=Sum('total_questions'),
        )
        osce_totals = request.user.osce_attempts.filter(total_questions__gt=0, **date_filters).aggregate(
            score=Sum(F('mcq_score') + F('practical_score')),
            total=Sum(F('total_questions') + F('practical_total')),
        )
        return (
            (exam_totals['score'] or 0) + (osce_totals['score'] or 0),
            (exam_totals['total'] or 0) + (osce_totals['total'] or 0),
        )

    score_total, questions_total = score_totals_between()
    average_score = round((score_total / questions_total) * 100) if questions_total else 0
    current_week_score, current_week_total = score_totals_between(week_start, today + timedelta(days=1))
    previous_week_start = week_start - timedelta(days=7)
    previous_week_score, previous_week_total = score_totals_between(previous_week_start, week_start)
    current_week_average = round((current_week_score / current_week_total) * 100) if current_week_total else 0
    previous_week_average = round((previous_week_score / previous_week_total) * 100) if previous_week_total else None
    average_score_change = current_week_average - previous_week_average if previous_week_average is not None else None
    average_score_change_display = f'{average_score_change:+d}' if average_score_change is not None else None
    modules_by_year = {year: [] for year in range(1, 6)}
    quizzes_by_year = {year: [] for year in range(1, 6)}
    osce_exams_by_year = {year: [] for year in range(1, 6)}
    modules = Module.objects.filter(is_active=True).annotate(
        total_exams=Count('exams', filter=Q(exams__is_active=True), distinct=True),
        completed_exams=Count(
            'exams',
            filter=Q(
                exams__is_active=True,
                exams__attempts__student=request.user,
                exams__attempts__total_questions__gt=0,
            ),
            distinct=True,
        ),
        total_osce_exams=Count(
            'osce_exams',
            filter=Q(osce_exams__is_active=True),
            distinct=True,
        ),
        completed_osce_exams=Count(
            'osce_exams',
            filter=Q(
                osce_exams__is_active=True,
                osce_exams__attempts__student=request.user,
                osce_exams__attempts__total_questions__gt=0,
            ),
            distinct=True,
        ),
        last_access=Max(
            'exams__attempts__submitted_at',
            filter=Q(exams__attempts__student=request.user),
        ),
    ).order_by('year', 'order', 'name')
    for module in modules:
        section_count = sum((
            module.has_lessons,
            module.has_videos,
            module.has_files,
            module.has_text,
            module.has_exams,
            module.has_osce,
        ))
        total_quizzes = module.total_exams + module.total_osce_exams
        completed_quizzes = module.completed_exams + module.completed_osce_exams
        progress = round((completed_quizzes / total_quizzes) * 100) if total_quizzes else 0
        if total_quizzes and completed_quizzes == total_quizzes:
            status, status_class = 'Completed', 'status-completed'
        elif module.last_access:
            status, status_class = 'In Progress', 'status-progress'
        else:
            status, status_class = 'Not Started', 'status-not-started'

        if not module.last_access:
            last_access = '-'
        else:
            days_since_access = (timezone.localdate() - timezone.localdate(module.last_access)).days
            if days_since_access == 0:
                last_access = 'Today'
            elif days_since_access == 1:
                last_access = 'Yesterday'
            else:
                last_access = f'{days_since_access} days ago'
        modules_by_year[module.year].append({
            'id': module.pk,
            'name': module.name,
            'url': reverse('module-detail', args=[module.pk]),
            'imageUrl': module.colored_image_url,
            'bg': module.bg_color,
            'color': module.color,
            'btnColor': module.btn_color,
            'sections': section_count,
            'description': module.description,
            'progress': progress,
            'completedQuizzes': completed_quizzes,
            'totalQuizzes': total_quizzes,
            'status': status,
            'statusClass': status_class,
            'lastAccess': last_access,
        })

    exams = Exam.objects.filter(
        is_active=True,
        module__is_active=True,
    ).select_related('module', 'subject', 'week').prefetch_related('questions', 'attempts')
    for exam in exams:
        is_locked = not can_access_content(request.user, exam)
        attempts = [attempt for attempt in exam.attempts.all() if attempt.student_id == request.user.id]
        completed_attempts = [attempt for attempt in attempts if attempt.total_questions > 0]
        first_attempt = min(
            completed_attempts,
            key=lambda attempt: (attempt.submitted_at, attempt.pk),
            default=None,
        )
        retries_available = max(exam.retry_times - len(attempts), 0)
        if not first_attempt:
            score, badge = 'Not Answered', 'bg-secondary'
        elif exam.exam_type == 'saq':
            score, badge = '-/-', 'bg-secondary'
        else:
            percentage = round((first_attempt.score / first_attempt.total_questions) * 100) if first_attempt.total_questions else 0
            score = f'{percentage}%'
            badge = 'bg-success' if percentage >= 75 else ('bg-warning' if percentage >= 50 else 'bg-danger')
        quizzes_by_year[exam.year].append({
            'url': reverse('exam-detail', args=[exam.pk]),
            'title': exam.name,
            'module': exam.module.name,
            'subject': exam.subject.name if exam.subject_id else '',
            'week': exam.week.name if exam.week_id else '',
            'type': exam.exam_type,
            'qs': len(exam.questions.all()),
            'retries': retries_available,
            'score': score,
            'badge': badge,
            'hasFirstAttempt': bool(first_attempt),
            'reviewUrl': reverse('exam-review', args=[exam.pk]) if first_attempt else '',
            'isLocked': is_locked,
            'canStart': not is_locked and bool(exam.questions.all()) and retries_available > 0,
            'status': 'Premium required' if is_locked else ('Completed' if retries_available == 0 else ('Unavailable' if not exam.questions.all() else 'Available')),
            'statusClass': 'bg-secondary' if is_locked or retries_available == 0 else ('bg-light text-muted' if not exam.questions.all() else badge),
        })

    osce_exams = OSCEExam.objects.filter(
        is_active=True,
        module__is_active=True,
    ).select_related('module').prefetch_related('questions')
    for exam in osce_exams:
        is_locked = not can_access_content(request.user, exam)
        attempts_used = OSCEAttempt.objects.filter(exam=exam, student=request.user).count()
        retries_available = max(exam.retry_times - attempts_used, 0)
        osce_exams_by_year[exam.year].append({
            'url': reverse('osce-detail', args=[exam.pk]),
            'title': exam.name,
            'module': exam.module.name,
            'station': exam.osce_station,
            'stationLabel': exam.get_osce_station_display(),
            'qs': exam.graded_question_count,
            'time': exam.mcq_timer,
            'retries': retries_available,
            'isLocked': is_locked,
            'canStart': not is_locked and exam.question_count > 0 and retries_available > 0,
        })

    years = [
        {
            'number': year,
            'module_count': len(modules_by_year[year]),
            'courses': modules_by_year[year],
        }
        for year in range(1, 6)
    ]
    note_filter_year = request.GET.get('note_year', '')
    note_filter_module = request.GET.get('note_module', '')
    note_filter_date = request.GET.get('note_date', '')
    note_filters = {}
    if note_filter_year.isdigit() and int(note_filter_year) in range(1, 6):
        note_filters['year'] = int(note_filter_year)
    if note_filter_module.isdigit():
        note_filters['module_id'] = int(note_filter_module)
    if parse_date(note_filter_date):
        note_filters['date__date'] = note_filter_date
    notes = Note.objects.filter(student=request.user, **note_filters).select_related('module')

    leaderboard_progress = list(
        StudentProgress.objects.filter(
            student__role='student',
            student__is_staff=False,
            student__is_superuser=False,
        ).select_related('student').order_by('-total_points', 'student_id')[:10]
    )
    leaderboard_student_ids = [progress.student_id for progress in leaderboard_progress]
    exam_leaderboard_totals = {
        row['student_id']: row
        for row in ExamAttempt.objects.filter(
            student_id__in=leaderboard_student_ids,
            total_questions__gt=0,
        ).values('student_id').annotate(score=Sum('score'), total=Sum('total_questions'))
    }
    osce_leaderboard_totals = {
        row['student_id']: row
        for row in OSCEAttempt.objects.filter(
            student_id__in=leaderboard_student_ids,
            total_questions__gt=0,
        ).values('student_id').annotate(
            score=Sum(F('mcq_score') + F('practical_score')),
            total=Sum(F('total_questions') + F('practical_total')),
        )
    }
    leaderboard = []
    for position, progress in enumerate(leaderboard_progress, start=1):
        exam_total = exam_leaderboard_totals.get(progress.student_id, {})
        osce_total = osce_leaderboard_totals.get(progress.student_id, {})
        leaderboard_score = (exam_total.get('score') or 0) + (osce_total.get('score') or 0)
        leaderboard_questions = (exam_total.get('total') or 0) + (osce_total.get('total') or 0)
        leaderboard.append({
            'position': position,
            'student_id': progress.student_id,
            'name': progress.student.get_full_name() or progress.student.username,
            'rank': progress.rank,
            'xp': progress.total_points,
            'average_score': round((leaderboard_score / leaderboard_questions) * 100) if leaderboard_questions else 0,
        })

    badge_progress = list(
        Badge.objects.filter(awards__student=request.user).annotate(
            earned_count=Count('awards'),
            last_awarded_at=Max('awards__awarded_at'),
        ).order_by('-last_awarded_at')[:12]
    )
    for badge in badge_progress:
        badge.points_earned = badge.xp_reward * badge.earned_count

    return render(request, 'dashboard/home.html', {
        'active_page': 'dashboard',
        'student_progress': student_progress,
        'rank': rank,
        'rank_percent': round(rank_percent),
        'questions_solved_this_week': questions_solved_this_week,
        'weekly_goal_data': weekly_goal_data,
        'xp_chart_data': xp_chart_data,
        'badges_earned_count': badges_earned.count(),
        'badges_earned_today': badges_earned_today,
        'day_streak': day_streak,
        'average_score': average_score,
        'average_score_change': average_score_change,
        'average_score_change_display': average_score_change_display,
        'badges': StudentBadge.objects.filter(student=request.user).select_related('badge')[:12],
        'badge_progress': badge_progress,
        'years': years,
        'modules_by_year': modules_by_year,
        'quizzes_by_year': quizzes_by_year,
        'osce_exams_by_year': osce_exams_by_year,
        'notes': notes,
        'note_modules': Module.objects.filter(is_active=True).order_by('year', 'order', 'name'),
        'note_filter_year': note_filter_year,
        'note_filter_module': note_filter_module,
        'note_filter_date': note_filter_date,
        'leaderboard': leaderboard,
        'telegram_group_url': _telegram_group_for(request.user.academic_year).public_url,
    })


def _telegram_group_for(academic_year):
    """Return the configured group, retaining the original feed as a safe fallback."""
    return TelegramGroup.objects.filter(year=academic_year).first() or TelegramGroup(
        year=academic_year or 1, handle='medmaster012'
    )


@login_required(login_url='auth')
def telegram_feed(request):
    group = _telegram_group_for(request.user.academic_year)
    try:
        res = requests.get(group.preview_url, timeout=10)
        res.raise_for_status()
    except requests.RequestException:
        return JsonResponse([], safe=False)

    soup = BeautifulSoup(res.text, "html.parser")

    messages = []

    for msg in soup.select(".tgme_widget_message"):

        text_el = msg.select_one(".tgme_widget_message_text")
        text = text_el.get_text(" ", strip=True) if text_el else ""

        date_el = msg.select_one("time")
        date = date_el["datetime"] if date_el else ""

        post_attr = msg.get("data-post")
        link = f"https://t.me/{post_attr}" if post_attr else ""

        # 🔥 detect files
        has_document = msg.select_one(".tgme_widget_message_document")
        has_photo = msg.select_one(".tgme_widget_message_photo")
        has_video = msg.select_one(".tgme_widget_message_video")

        has_file = any([has_document, has_photo, has_video])

        # 💀 أهم سطر
        if not text and not has_file:
            continue  # تجاهل الفاضي

        messages.append({
            "text": text if text else "📎 File attached",
            "date": date,
            "hasFile": has_file,
            "link": link
        })

    return JsonResponse(messages[:10], safe=False)
