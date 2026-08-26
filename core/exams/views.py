from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Exam, ExamAnswer, ExamAttempt, MCQAnswer
from progress.services import award_exam_badges, record_answer_points
from verification.services import can_access_content


def _attempts_used(exam, user):
    return ExamAttempt.objects.filter(exam=exam, student=user).count()


def _question_results(attempt):
    answer_records = attempt.answers.select_related('question', 'selected_answer').prefetch_related(
        'question__answers'
    ).order_by('question__order', 'question__pk')
    question_results = []
    for answer_record in answer_records:
        correct_answer = next(
            (answer for answer in answer_record.question.answers.all() if answer.is_correct), None
        )
        question_results.append({
            'answer_record': answer_record,
            'correct_answer': correct_answer,
            'is_correct': bool(answer_record.selected_answer and answer_record.selected_answer.is_correct),
        })
    return question_results


@login_required(login_url='auth')
def exam_detail(request, pk):
    exam = get_object_or_404(
        Exam.objects.select_related('module').prefetch_related('questions__answers'),
        pk=pk,
        is_active=True,
        module__is_active=True,
    )
    if not can_access_content(request.user, exam):
        raise PermissionDenied('This exam requires activation for your academic year.')
    allowed_attempts = exam.retry_times
    attempts_used = _attempts_used(exam, request.user)
    if attempts_used >= allowed_attempts:
        messages.error(request, 'You have used all available attempts for this exam.')
        return redirect('module-detail', pk=exam.module_id)
    if not exam.questions.exists():
        messages.error(request, 'This exam has no questions yet.')
        return redirect('module-detail', pk=exam.module_id)
    attempt = ExamAttempt.objects.create(exam=exam, student=request.user)
    attempts_used += 1
    question_data = [
        {
            'id': question.pk,
            'text': question.text,
            'image_url': question.image_url,
            'explanation': question.answer_explanation,
            'is_saq': exam.exam_type == 'saq',
            'answers': [
                {'id': answer.pk, 'text': answer.text, 'is_correct': answer.is_correct}
                for answer in question.answers.all()
            ],
        }
        for question in exam.questions.all()
    ]
    return render(request, 'exams/exam.html', {
        'exam': exam,
        'attempt_id': attempt.pk,
        'attempts_remaining': allowed_attempts - attempts_used,
        'question_data': question_data,
    })


@login_required(login_url='auth')
@transaction.atomic
def submit_exam(request, pk):
    if request.method != 'POST':
        raise Http404
    exam = get_object_or_404(Exam.objects.prefetch_related('questions__answers'), pk=pk, is_active=True)
    if not can_access_content(request.user, exam):
        raise PermissionDenied('This exam requires activation for your academic year.')
    attempt = ExamAttempt.objects.filter(
        pk=request.POST.get('attempt_id'), exam=exam, student=request.user, total_questions=0
    ).first()
    if not attempt:
        messages.error(request, 'This exam attempt is no longer available.')
        return redirect('module-detail', pk=exam.module_id)

    questions = list(exam.questions.all())
    score = 0
    answers = []
    for question in questions:
        if exam.exam_type == 'saq':
            answers.append(ExamAnswer(
                attempt=attempt,
                question=question,
                text_answer=request.POST.get(f'question_text_{question.pk}', ''),
            ))
        else:
            selected_id = request.POST.get(f'question_{question.pk}')
            selected = question.answers.filter(pk=selected_id).first() if selected_id else None
            if selected and selected.is_correct:
                score += 1
            answers.append(ExamAnswer(attempt=attempt, question=question, selected_answer=selected))
    ExamAnswer.objects.bulk_create(answers)
    attempt.score = score
    attempt.total_questions = len(questions)
    attempt.save(update_fields=('score', 'total_questions'))
    answer_records = attempt.answers.select_related('question', 'selected_answer').prefetch_related(
        'question__answers'
    ).order_by('question__order', 'question__pk')
    if exam.exam_type != 'saq':
        for answer_record in answer_records:
            # An unanswered item was not solved, so it earns neither points nor a deduction.
            if answer_record.selected_answer_id:
                is_correct = answer_record.selected_answer.is_correct
                record_answer_points(
                    student=request.user,
                    source_key=f'exam-answer:{attempt.pk}:{answer_record.question_id}',
                    source_label=f'{exam.name} — question {answer_record.question.order}',
                    is_correct=is_correct,
                )
        is_first_completed_attempt = not ExamAttempt.objects.filter(
            exam=exam,
            student=request.user,
            total_questions__gt=0,
        ).exclude(pk=attempt.pk).exists()
        if is_first_completed_attempt:
            award_exam_badges(
                student=request.user,
                score=attempt.score,
                total_questions=attempt.total_questions,
                attempt_key=f'exam:{attempt.pk}',
            )
    attempts_remaining = max(exam.retry_times - _attempts_used(exam, request.user), 0)
    return render(request, 'exams/result.html', {
        'exam': exam,
        'attempt': attempt,
        'question_results': _question_results(attempt),
        'attempts_remaining': attempts_remaining,
    })


@login_required(login_url='auth')
def exam_review(request, pk):
    """Show the student's first completed attempt without creating a new attempt."""
    exam = get_object_or_404(
        Exam.objects.select_related('module'),
        pk=pk,
        is_active=True,
        module__is_active=True,
    )
    if not can_access_content(request.user, exam):
        raise PermissionDenied('This exam requires activation for your academic year.')
    attempt = ExamAttempt.objects.filter(
        exam=exam,
        student=request.user,
        total_questions__gt=0,
    ).order_by('submitted_at', 'pk').first()
    if not attempt:
        messages.error(request, 'Complete this quiz before reviewing it.')
        return redirect('home')
    return render(request, 'exams/result.html', {
        'exam': exam,
        'attempt': attempt,
        'question_results': _question_results(attempt),
        'review_mode': True,
    })
