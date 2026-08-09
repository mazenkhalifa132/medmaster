from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, ModelForm, Select
import nested_admin

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
    fields = (
        'year', 'module', 'name', 'retry_times', 'mcq_timer', 'osce_station',
        'systolic_pressure', 'diastolic_pressure',
        'ecg_v1', 'ecg_v2', 'ecg_v3', 'ecg_v4', 'ecg_v5', 'ecg_v6',
        'is_active',
    )
    list_display = (
        'name', 'year', 'module', 'mcq_timer', 'osce_station',
        'retry_times', 'question_count', 'is_active',
    )
    list_filter = ('year', 'module', 'osce_station', 'is_active')
    search_fields = ('name', 'module__name')
    ordering = ('year', 'module__order', 'name')


@admin.register(OSCEQuestion)
class OSCEQuestionAdmin(nested_admin.NestedModelAdmin):
    inlines = (OSCEAnswerInline,)
    list_display = ('exam', 'order', 'question')
    list_filter = ('exam__year', 'exam__module')
    search_fields = ('question', 'exam__name')
    ordering = ('exam', 'order')

    def has_module_permission(self, request):
        return False
