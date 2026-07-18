from django.contrib import admin
from django.forms import ModelForm, Select

from .models import StudyFile


class ModuleByYearSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-year'] = value.instance.year
        return option


class StudyFileAdminForm(ModelForm):
    class Meta:
        model = StudyFile
        fields = '__all__'
        widgets = {'module': ModuleByYearSelect}

    class Media:
        js = ('exams/admin/exam_module_filter.js',)


@admin.register(StudyFile)
class StudyFileAdmin(admin.ModelAdmin):
    form = StudyFileAdminForm
    list_display = ('file_name', 'file_type', 'file_size', 'year', 'module')
    list_filter = ('year', 'file_type', 'module')
    search_fields = ('file_name', 'module__name')
    ordering = ('year', 'module__order', 'file_name')
    fields = ('year', 'module', 'file_name', 'file_size', 'file_type', 'file_link')
