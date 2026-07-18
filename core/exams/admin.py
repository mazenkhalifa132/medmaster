from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, ModelForm, Select
import nested_admin

from .models import Exam, ExamAnswer, ExamAttempt, ExamQuestion, MCQAnswer


class ModuleByYearSelect(Select):
    """Expose each module's year to the admin JavaScript filter."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-year'] = value.instance.year
        return option


class ExamAdminForm(ModelForm):
    class Meta:
        model = Exam
        fields = '__all__'
        widgets = {'module': ModuleByYearSelect}

    class Media:
        js = ('exams/admin/exam_module_filter.js',)


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
    fields = ('order', 'text', 'is_correct')


class ExamQuestionInline(nested_admin.NestedStackedInline):
    model = ExamQuestion
    extra = 1
    fields = ('order', 'text', 'image_url', 'answer_explanation')
    inlines = (MCQAnswerInline,)


@admin.register(Exam)
class ExamAdmin(nested_admin.NestedModelAdmin):
    form = ExamAdminForm
    inlines = (ExamQuestionInline,)
    list_display = ('name', 'exam_type', 'year', 'module', 'time_limit', 'retry_times', 'result', 'is_active')
    list_filter = ('exam_type', 'year', 'module', 'is_active')
    search_fields = ('name', 'module__name')
    ordering = ('year', 'module__order', 'name')
    fields = ('year', 'module', 'name', 'exam_type', 'time_limit', 'retry_times', 'is_active')

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


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'total_questions', 'submitted_at')
    list_filter = ('exam', 'submitted_at')
    search_fields = ('student__username', 'student__email', 'exam__name')
    readonly_fields = ('exam', 'student', 'score', 'total_questions', 'submitted_at')

    def has_add_permission(self, request):
        return False


@admin.register(ExamAnswer)
class ExamAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'selected_answer', 'text_answer')
    readonly_fields = ('attempt', 'question', 'selected_answer', 'text_answer')

    def has_add_permission(self, request):
        return False
