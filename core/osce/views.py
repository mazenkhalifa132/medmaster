from html import escape, unescape
from html.parser import HTMLParser

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import OSCEAnswerRecord, OSCEAttempt, OSCEExam


class PracticalDetailsSanitizer(HTMLParser):
    """Keep the small, presentational HTML emitted by OSCE stations safe to render."""

    allowed_tags = {'div', 'small', 'strong'}
    allowed_class_tokens = {
        'd-block', 'mt-2', 'text-danger', 'text-muted', 'text-success',
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.allowed_tags:
            return
        class_value = next((value for name, value in attrs if name == 'class'), '') or ''
        classes = [name for name in class_value.split() if name in self.allowed_class_tokens]
        class_attribute = f' class=\"{escape(" ".join(classes), quote=True)}\"' if classes else ''
        self.parts.append(f'<{tag}{class_attribute}>')

    def handle_endtag(self, tag):
        if tag in self.allowed_tags:
            self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        self.parts.append(escape(data))


def sanitize_practical_details(value):
    sanitizer = PracticalDetailsSanitizer()
    # Detail markup can arrive HTML-escaped when a browser or intermediary
    # serializes the hidden form field. Decode it before applying the strict
    # allow-list so it renders as formatted station feedback, not literal tags.
    sanitizer.feed(unescape(value))
    sanitizer.close()
    return ''.join(sanitizer.parts)


@login_required(login_url='auth')
def osce_detail(request, pk):
    exam = get_object_or_404(
        OSCEExam.objects.select_related('module').prefetch_related('questions__answers'),
        pk=pk,
        is_active=True,
        module__is_active=True,
    )
    if not exam.questions.exists():
        messages.error(request, 'This OSCE has no questions yet.')
        return redirect('module-detail', pk=exam.module_id)

    allowed_attempts = exam.retry_times
    attempts_used = OSCEAttempt.objects.filter(exam=exam, student=request.user).count()
    if attempts_used >= allowed_attempts:
        messages.error(request, 'You have used all available attempts for this OSCE.')
        return redirect('module-detail', pk=exam.module_id)

    attempt = OSCEAttempt.objects.create(exam=exam, student=request.user)
    question_data = [
        {
            'id': question.pk,
            'text': question.question,
            'image_link': question.image_link,
            'explanation': question.explanation,
            'answers': [
                {'id': answer.pk, 'text': answer.text, 'is_correct': answer.is_correct}
                for answer in question.answers.all()
            ],
        }
        for question in exam.questions.all()
    ]
    return render(request, 'osce/osce.html', {
        'exam': exam,
        'attempt_id': attempt.pk,
        'attempt': attempt,
        'attempts_remaining': max(allowed_attempts - attempts_used - 1, 0),
        'question_data': question_data,
    })


@login_required(login_url='auth')
@transaction.atomic
def submit_osce(request, pk):
    if request.method != 'POST':
        raise Http404

    exam = get_object_or_404(OSCEExam.objects.prefetch_related('questions__answers'), pk=pk, is_active=True)
    attempt = OSCEAttempt.objects.filter(pk=request.POST.get('attempt_id'), exam=exam, student=request.user).first()
    if not attempt:
        messages.error(request, 'This OSCE attempt is no longer available.')
        return redirect('module-detail', pk=exam.module_id)

    practical_passed = request.POST.get('practical_passed') == 'on'
    practical_details = sanitize_practical_details(request.POST.get('practical_details', ''))
    try:
        practical_score = max(int(request.POST.get('practical_score', 0)), 0)
        practical_total = max(int(request.POST.get('practical_total', 0)), 0)
    except (TypeError, ValueError):
        practical_score = practical_total = 0
    # Each station supplies its own checklist score. Bound it to the checklist
    # configured for this OSCE, rather than trusting a browser-submitted total.
    if exam.osce_station in {'bp', 'ecg'}:
        # Every configured station is a single, all-or-nothing marked item.
        practical_total = 1
    practical_score = min(practical_score, practical_total)
    if exam.osce_station == 'none':
        practical_score = practical_total = 0
    attempt.practical_passed = practical_passed
    attempt.practical_details = practical_details
    attempt.practical_score = practical_score
    attempt.practical_total = practical_total

    questions = list(exam.questions.all())
    score = 0
    answer_records = []
    for question in questions:
        selected_id = request.POST.get(f'question_{question.pk}')
        selected = question.answers.filter(pk=selected_id).first() if selected_id else None
        if selected and selected.is_correct:
            score += 1
        answer_records.append(OSCEAnswerRecord(attempt=attempt, question=question, selected_answer=selected))

    OSCEAnswerRecord.objects.bulk_create(answer_records)
    attempt.mcq_score = score
    attempt.total_questions = len(questions)
    attempt.save(update_fields=('practical_passed', 'practical_details', 'practical_score', 'practical_total', 'mcq_score', 'total_questions'))

    answer_records = attempt.answers.select_related('question', 'selected_answer').prefetch_related('question__answers')
    question_results = []
    for answer_record in answer_records:
        correct_answer = next((answer for answer in answer_record.question.answers.all() if answer.is_correct), None)
        question_results.append({
            'answer_record': answer_record,
            'correct_answer': correct_answer,
            'is_correct': bool(answer_record.selected_answer and answer_record.selected_answer.is_correct),
        })

    attempts_remaining = max(exam.retry_times - OSCEAttempt.objects.filter(exam=exam, student=request.user).count(), 0)
    return render(request, 'osce/result.html', {
        'exam': exam,
        'attempt': attempt,
        'attempts_remaining': attempts_remaining,
        'question_results': question_results,
    })
