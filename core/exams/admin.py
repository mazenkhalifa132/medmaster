from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms import BaseInlineFormSet, ModelForm, Select
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.db.models import Max
import nested_admin

from .bulk_import import BulkQuestionImportError, parse_questions
from .models import Exam, ExamQuestion, MCQAnswer


class ModuleByYearSelect(Select):
    """Expose each module's year to the admin JavaScript filter."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-year'] = value.instance.year
        return option


class ModuleDependentSelect(Select):
    """Expose an exam setting's owning module to the admin JavaScript filter."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-module'] = value.instance.module_id
        return option


class ExamAdminForm(ModelForm):
    class Meta:
        model = Exam
        fields = '__all__'
        widgets = {
            'module': ModuleByYearSelect,
            'subject': ModuleDependentSelect,
            'week': ModuleDependentSelect,
        }

    class Media:
        js = ('exams/admin/exam_module_filter_v2.js',)


class AnswerInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if self.instance.exam.exam_type == 'saq':
            return
        correct_answers = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                continue
            if form.cleaned_data and form.cleaned_data.get('is_correct'):
                correct_answers += 1
        if correct_answers != 1:
            raise ValidationError('Each question must have exactly one correct answer.')


class MCQAnswerInline(nested_admin.NestedTabularInline):
    model = MCQAnswer
    formset = AnswerInlineFormSet
    extra = 2
    can_delete = False
    fields = ('order', 'text', 'is_correct')


class ExamQuestionInline(nested_admin.NestedStackedInline):
    model = ExamQuestion
    extra = 1
    can_delete = True
    fields = ('order', 'text', 'image_url', 'answer_explanation')
    inlines = (MCQAnswerInline,)


@admin.register(Exam)
class ExamAdmin(nested_admin.NestedModelAdmin):
    form = ExamAdminForm
    inlines = (ExamQuestionInline,)
    change_form_template = 'admin/exams/exam/change_form.html'
    list_display = ('name', 'order', 'exam_type', 'year', 'module', 'time_limit', 'retry_times', 'is_trial', 'result', 'is_active')
    list_filter = ('exam_type', 'year', 'module', 'subject', 'week', 'is_trial', 'is_active')
    search_fields = ('name', 'module__name')
    ordering = ('year', 'module__order', 'order', 'name')
    fields = ('year', 'module', 'subject', 'week', 'order', 'name', 'exam_type', 'time_limit', 'retry_times', 'is_trial', 'is_active')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/bulk-upload/',
                self.admin_site.admin_view(self.bulk_upload_view),
                name='exams_exam_bulk_upload',
            ),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request, object_id):
        exam = self.get_object(request, object_id)
        if exam is None:
            return HttpResponseRedirect(reverse('admin:exams_exam_changelist'))
        if not self.has_change_permission(request, exam):
            raise PermissionDenied
        if exam.exam_type == 'saq':
            self.message_user(
                request, 'Bulk MCQ import is not available for SAQ exams.', messages.ERROR
            )
            return HttpResponseRedirect(reverse('admin:exams_exam_change', args=(exam.pk,)))

        raw_text = request.POST.get('questions', '')
        if request.method == 'POST':
            try:
                question_rows = parse_questions(raw_text)
                with transaction.atomic():
                    exam = Exam.objects.select_for_update().get(pk=exam.pk)
                    last_order = exam.questions.aggregate(max_order=Max('order'))['max_order'] or 0
                    questions = [
                        ExamQuestion(
                            exam=exam,
                            order=last_order + index,
                            text=row['text'],
                            answer_explanation=row['explanation'],
                        )
                        for index, row in enumerate(question_rows, start=1)
                    ]
                    created_questions = ExamQuestion.objects.bulk_create(questions)
                    answers = [
                        MCQAnswer(
                            question=question,
                            order=answer_order,
                            text=answer['text'],
                            is_correct=answer['is_correct'],
                        )
                        for question, row in zip(created_questions, question_rows)
                        for answer_order, answer in enumerate(row['answers'], start=1)
                    ]
                    MCQAnswer.objects.bulk_create(answers)
            except BulkQuestionImportError as error:
                self.message_user(request, str(error), messages.ERROR)
            else:
                self.message_user(
                    request,
                    f'Imported {len(question_rows)} question(s) and their answers.',
                    messages.SUCCESS,
                )
                return HttpResponseRedirect(reverse('admin:exams_exam_change', args=(exam.pk,)))

        context = {
            **self.admin_site.each_context(request),
            'title': f'Import questions: {exam.name}',
            'exam': exam,
            'raw_text': raw_text,
        }
        return TemplateResponse(request, 'admin/exams/exam/bulk_upload.html', context)

@admin.register(ExamQuestion)
class ExamQuestionAdmin(nested_admin.NestedModelAdmin):
    inlines = (MCQAnswerInline,)
    list_display = ('exam', 'order', 'text')
    list_filter = ('exam__year', 'exam__module')
    search_fields = ('text', 'exam__name')
    ordering = ('exam', 'order')

    def has_module_permission(self, request):
        """Questions are managed from the Exam editor, not as a top-level section."""
        return False
