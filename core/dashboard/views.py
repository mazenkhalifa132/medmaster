from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from exams.models import Exam
from modules.models import Module
from notes.models import Note
from osce.models import OSCEAttempt, OSCEExam


@login_required(login_url='auth')
def home(request):
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
            'icon': module.icon_class or 'bx-book',
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
    ).select_related('module').prefetch_related('questions', 'attempts')
    for exam in exams:
        attempts = [attempt for attempt in exam.attempts.all() if attempt.student_id == request.user.id]
        completed_attempts = [attempt for attempt in attempts if attempt.total_questions > 0]
        first_attempt = min(
            completed_attempts,
            key=lambda attempt: (attempt.submitted_at, attempt.pk),
            default=None,
        )
        retries_available = max(exam.retry_times - len(attempts), 0)
        if not first_attempt or exam.exam_type == 'saq':
            score, badge = 'Pending', 'bg-secondary'
        else:
            percentage = round((first_attempt.score / first_attempt.total_questions) * 100) if first_attempt.total_questions else 0
            score = f'{percentage}%'
            badge = 'bg-success' if percentage >= 75 else ('bg-warning' if percentage >= 50 else 'bg-danger')
        quizzes_by_year[exam.year].append({
            'url': reverse('exam-detail', args=[exam.pk]),
            'title': exam.name,
            'module': exam.module.name,
            'type': exam.exam_type,
            'qs': len(exam.questions.all()),
            'retries': retries_available,
            'score': score,
            'badge': badge,
        })

    osce_exams = OSCEExam.objects.filter(
        is_active=True,
        module__is_active=True,
    ).select_related('module').prefetch_related('questions')
    for exam in osce_exams:
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
            'canStart': exam.question_count > 0 and retries_available > 0,
        })

    years = [
        {
            'number': year,
            'module_count': len(modules_by_year[year]),
            'courses': modules_by_year[year],
        }
        for year in range(1, 6)
    ]
    return render(request, 'dashboard/home.html', {
        'active_page': 'dashboard',
        'years': years,
        'modules_by_year': modules_by_year,
        'quizzes_by_year': quizzes_by_year,
        'osce_exams_by_year': osce_exams_by_year,
        'notes': Note.objects.filter(student=request.user).select_related('module'),
        'note_modules': Module.objects.filter(is_active=True).order_by('year', 'order', 'name'),
    })
