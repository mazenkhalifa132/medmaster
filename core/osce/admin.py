from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.forms import BaseInlineFormSet, ModelForm, Select
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
import nested_admin

from exams.bulk_import import BulkQuestionImportError, parse_questions
from .models import OSCEAnswer, OSCEExam, OSCEQuestion


class ModuleByYearSelect(Select):
    """Expose module years so the module list can be filtered in the admin."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-year'] = value.instance.year
        return option


class OSCEExamAdminForm(ModelForm):
    class Meta:
        model = OSCEExam
        fields = '__all__'
        widgets = {'module': ModuleByYearSelect}

    class Media:
        js = (
            'exams/admin/exam_module_filter.js',
            'osce/admin/osce_station_fields.js',
        )


class AnswerInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        correct_answers = sum(
            1
            for form in self.forms
            if hasattr(form, 'cleaned_data')
            and form.cleaned_data
            and not form.cleaned_data.get('DELETE')
            and form.cleaned_data.get('is_correct')
        )
        if correct_answers != 1:
            raise ValidationError('Each question must have exactly one correct answer.')


class OSCEAnswerInline(nested_admin.NestedTabularInline):
    model = OSCEAnswer
    formset = AnswerInlineFormSet
    extra = 2
    fields = ('order', 'text', 'is_correct')


class OSCEQuestionInline(nested_admin.NestedStackedInline):
    model = OSCEQuestion
    extra = 1
    fields = ('order', 'question', 'image_link', 'explanation')
    inlines = (OSCEAnswerInline,)


@admin.register(OSCEExam)
class OSCEExamAdmin(nested_admin.NestedModelAdmin):
    form = OSCEExamAdminForm
    inlines = (OSCEQuestionInline,)
    change_form_template = 'admin/osce/osceexam/change_form.html'
    fields = (
        'year', 'module', 'name', 'retry_times', 'mcq_timer', 'is_trial', 'osce_station',
        'systolic_pressure', 'diastolic_pressure',
        'ecg_v1', 'ecg_v2', 'ecg_v3', 'ecg_v4', 'ecg_v5', 'ecg_v6',
        'is_active',
    )
    list_display = (
        'name', 'year', 'module', 'mcq_timer', 'osce_station',
        'retry_times', 'question_count', 'is_trial', 'is_active',
    )
    list_filter = ('year', 'module', 'osce_station', 'is_trial', 'is_active')
    search_fields = ('name', 'module__name')
    ordering = ('year', 'module__order', 'name')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/bulk-upload/',
                self.admin_site.admin_view(self.bulk_upload_view),
                name='osce_osceexam_bulk_upload',
            ),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request, object_id):
        exam = self.get_object(request, object_id)
        if exam is None:
            return HttpResponseRedirect(reverse('admin:osce_osceexam_changelist'))
        if not self.has_change_permission(request, exam):
            raise PermissionDenied

        raw_text = request.POST.get('questions', '')
        if request.method == 'POST':
            try:
                question_rows = parse_questions(raw_text)
                with transaction.atomic():
                    exam = OSCEExam.objects.select_for_update().get(pk=exam.pk)
                    last_order = exam.questions.aggregate(max_order=Max('order'))['max_order'] or 0
                    questions = [
                        OSCEQuestion(
                            exam=exam,
                            order=last_order + index,
                            question=row['text'],
                            explanation=row['explanation'],
                        )
                        for index, row in enumerate(question_rows, start=1)
                    ]
                    created_questions = OSCEQuestion.objects.bulk_create(questions)
                    answers = [
                        OSCEAnswer(
                            question=question,
                            order=answer_order,
                            text=answer['text'],
                            is_correct=answer['is_correct'],
                        )
                        for question, row in zip(created_questions, question_rows)
                        for answer_order, answer in enumerate(row['answers'], start=1)
                    ]
                    OSCEAnswer.objects.bulk_create(answers)
            except BulkQuestionImportError as error:
                self.message_user(request, str(error), messages.ERROR)
            else:
                self.message_user(
                    request,
                    f'Imported {len(question_rows)} question(s) and their answers.',
                    messages.SUCCESS,
                )
                return HttpResponseRedirect(reverse('admin:osce_osceexam_change', args=(exam.pk,)))

        context = {
            **self.admin_site.each_context(request),
            'title': f'Import questions: {exam.name}',
            'exam': exam,
            'raw_text': raw_text,
        }
        return TemplateResponse(request, 'admin/osce/osceexam/bulk_upload.html', context)


@admin.register(OSCEQuestion)
class OSCEQuestionAdmin(nested_admin.NestedModelAdmin):
    inlines = (OSCEAnswerInline,)
    list_display = ('exam', 'order', 'question')
    list_filter = ('exam__year', 'exam__module')
    search_fields = ('question', 'exam__name')
    ordering = ('exam', 'order')

    def has_module_permission(self, request):
        return False
