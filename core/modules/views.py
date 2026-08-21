from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from exams.models import Exam
from files.models import StudyFile
from osce.models import OSCEAttempt, OSCEExam
from text.models import TextContent
from videos.models import Video, VideoWatch
from verification.services import can_access_content, has_year_access

from .models import Module


@login_required(login_url='auth')
def module_detail(request, pk):
    module = get_object_or_404(Module, pk=pk, is_active=True)
    is_year_activated = has_year_access(request.user, module.year)
    locked_content = {
        'videos': not is_year_activated and Video.objects.filter(module=module, is_trial=False).exists(),
        'files': not is_year_activated and StudyFile.objects.filter(module=module, is_trial=False).exists(),
        'exams': not is_year_activated and Exam.objects.filter(module=module, is_active=True, is_trial=False).exists(),
        'text': not is_year_activated and TextContent.objects.filter(
            module=module, status=TextContent.Status.PUBLISHED, is_trial=False
        ).exists(),
        'osce': not is_year_activated and OSCEExam.objects.filter(
            module=module, is_active=True, is_trial=False
        ).exists(),
    }
    exams = Exam.objects.filter(module=module, is_active=True).prefetch_related('questions')
    osce_exams = OSCEExam.objects.filter(module=module, is_active=True).prefetch_related('questions')
    study_files = list(
        StudyFile.objects.filter(module=module).select_related('subcategory').order_by(
            'subcategory__order', 'subcategory__name', 'file_name'
        )
    )
    grouped_files = {}
    uncategorized_files = []
    for study_file in study_files:
        if study_file.subcategory_id:
            grouped_files.setdefault(study_file.subcategory, []).append(study_file)
        else:
            uncategorized_files.append(study_file)
    file_groups = [
        {'name': subcategory.name, 'files': files}
        for subcategory, files in grouped_files.items()
    ]
    if uncategorized_files:
        file_groups.append({'name': 'Other files', 'files': uncategorized_files})
    videos = list(
        Video.objects.filter(module=module).select_related('subcategory').order_by(
            'subcategory__order', 'subcategory__name', 'name'
        )
    )
    watched_video_ids = set(
        VideoWatch.objects.filter(student=request.user, video__in=videos).values_list('video_id', flat=True)
    )
    grouped_videos = {}
    uncategorized_videos = []
    for video in videos:
        video.is_watched = video.pk in watched_video_ids
        if video.subcategory_id:
            grouped_videos.setdefault(video.subcategory, []).append(video)
        else:
            uncategorized_videos.append(video)
    video_groups = [
        {'name': subcategory.name, 'videos': videos}
        for subcategory, videos in grouped_videos.items()
    ]
    if uncategorized_videos:
        video_groups.append({'name': 'Other videos', 'videos': uncategorized_videos})
    text_contents = list(TextContent.objects.filter(
        module=module,
        status=TextContent.Status.PUBLISHED,
    ).select_related('author', 'subcategory').order_by(
        'subcategory__order', 'subcategory__name', 'title'
    ))
    grouped_text_contents = {}
    uncategorized_text_contents = []
    for text_content in text_contents:
        if text_content.subcategory_id:
            grouped_text_contents.setdefault(text_content.subcategory, []).append(text_content)
        else:
            uncategorized_text_contents.append(text_content)
    text_groups = [
        {'name': subcategory.name, 'text_contents': contents}
        for subcategory, contents in grouped_text_contents.items()
    ]
    if uncategorized_text_contents:
        text_groups.append({'name': 'Other text content', 'text_contents': uncategorized_text_contents})
    for study_file in study_files:
        study_file.is_locked = not can_access_content(request.user, study_file)
    for video in videos:
        video.is_locked = not can_access_content(request.user, video)
    for text_content in text_contents:
        text_content.is_locked = not can_access_content(request.user, text_content)
    readable_text_contents = [text_content for text_content in text_contents if not text_content.is_locked]
    exams_by_type = {}
    total_exams = exams.count()
    completed_exams = 0
    total_score = 0
    total_possible_score = 0
    for exam in exams:
        exam.is_locked = not can_access_content(request.user, exam)
        if exam.exam_type == 'saq':
            first_attempt = exam.attempts.filter(
                student=request.user, total_questions__gt=0
            ).order_by('submitted_at', 'pk').first()
            exam.student_result = '-/-' if first_attempt else 'Not Answered'
            if first_attempt:
                completed_exams += 1
            exam.attempts_used = exam.attempts.filter(student=request.user).count()
            exam.retries_remaining = max(exam.retry_times - exam.attempts_used, 0)
            exam.can_start = not exam.is_locked and exam.retries_remaining > 0
            exams_by_type.setdefault(exam.exam_type, []).append(exam)
            continue
        first_attempt = exam.attempts.filter(
            student=request.user, total_questions__gt=0
        ).order_by('submitted_at', 'pk').first()
        if first_attempt:
            completed_exams += 1
            total_score += first_attempt.score
            total_possible_score += first_attempt.total_questions
        exam.student_result = first_attempt.result if first_attempt else 'Not Answered'
        exam.attempts_used = exam.attempts.filter(student=request.user).count()
        exam.retries_remaining = max(exam.retry_times - exam.attempts_used, 0)
        exam.can_start = not exam.is_locked and exam.retries_remaining > 0
        exams_by_type.setdefault(exam.exam_type, []).append(exam)

    for osce_exam in osce_exams:
        osce_exam.is_locked = not can_access_content(request.user, osce_exam)
        first_attempt = OSCEAttempt.objects.filter(
            exam=osce_exam, student=request.user, total_questions__gt=0
        ).order_by('submitted_at', 'pk').first()
        osce_exam.student_result = first_attempt.grade_result if first_attempt else 'Not Answered'
        if first_attempt:
            total_score += first_attempt.total_score
            total_possible_score += first_attempt.total_possible_score
        osce_exam.attempts_used = OSCEAttempt.objects.filter(
            exam=osce_exam, student=request.user
        ).count()
        osce_exam.retries_remaining = max(osce_exam.retry_times - osce_exam.attempts_used, 0)
        osce_exam.can_start = not osce_exam.is_locked and osce_exam.question_count > 0 and osce_exam.retries_remaining > 0

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
            'total_files': len(study_files),
            'file_groups': file_groups,
            'video_groups': video_groups,
            'text_groups': text_groups,
            'text_contents': readable_text_contents,
            'osce_exams': osce_exams,
            'total_osce_exams': osce_exams.count(),
            'is_year_activated': is_year_activated,
            'locked_content': locked_content,
        },
    )


@login_required(login_url='auth')
@require_POST
def mark_video_watched(request, pk):
    video = get_object_or_404(Video, pk=pk, module__is_active=True)
    if not can_access_content(request.user, video):
        return JsonResponse({'detail': 'This video requires activation for your academic year.'}, status=403)
    VideoWatch.objects.get_or_create(student=request.user, video=video)
    return JsonResponse({'watched': True})
