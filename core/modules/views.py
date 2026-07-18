from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from exams.models import Exam
from files.models import StudyFile

from .models import Module


@login_required(login_url='auth')
def module_detail(request, pk):
    module = get_object_or_404(Module, pk=pk, is_active=True)
    exams = Exam.objects.filter(module=module, is_active=True).prefetch_related('questions')
    study_files = StudyFile.objects.filter(module=module)
    exams_by_type = {}
    total_exams = exams.count()
    completed_exams = 0
    total_score = 0
    total_possible_score = 0
    for exam in exams:
        if exam.exam_type == 'saq':
            exam.student_result = '-/-'
            if exam.attempts.filter(student=request.user, total_questions__gt=0).exists():
                completed_exams += 1
            exam.attempts_used = exam.attempts.filter(student=request.user).count()
            exam.retries_remaining = max(exam.retry_times - exam.attempts_used, 0)
            exam.can_start = exam.retries_remaining > 0
            exams_by_type.setdefault(exam.exam_type, []).append(exam)
            continue
        first_attempt = exam.attempts.filter(
            student=request.user, total_questions__gt=0
        ).order_by('submitted_at', 'pk').first()
        if first_attempt:
            completed_exams += 1
            total_score += first_attempt.score
            total_possible_score += first_attempt.total_questions
        exam.student_result = first_attempt.result if first_attempt else f'0/{exam.question_count}'
        exam.attempts_used = exam.attempts.filter(student=request.user).count()
        exam.retries_remaining = max(exam.retry_times - exam.attempts_used, 0)
        exam.can_start = exam.retries_remaining > 0
        exams_by_type.setdefault(exam.exam_type, []).append(exam)

    exam_progress = round((completed_exams / total_exams) * 100) if total_exams else 0
    average_exam_score = round((total_score / total_possible_score) * 100) if total_possible_score else 0

    exam_groups = [
        {
            'label': label,
            'exams': exams_by_type[exam_type],
        }
        for exam_type, label in Exam.EXAM_TYPE_CHOICES
        if exam_type in exams_by_type
    ]
    return render(
        request,
        'modules/module.html',
        {
            'module': module,
            'exam_groups': exam_groups,
            'total_exams': total_exams,
            'completed_exams': completed_exams,
            'exam_progress': exam_progress,
            'average_exam_score': average_exam_score,
            'study_files': study_files,
            'total_files': study_files.count(),
        },
    )
