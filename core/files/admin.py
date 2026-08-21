from django.contrib import admin
from django.forms import ModelForm, Select

from .models import FileSubcategory, StudyFile


class ModuleByYearSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-year'] = value.instance.year
        return option


class SubcategoryByModuleSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-module'] = value.instance.module_id
        return option


class StudyFileAdminForm(ModelForm):
    class Meta:
        model = StudyFile
        fields = '__all__'
        widgets = {
            'module': ModuleByYearSelect,
            'subcategory': SubcategoryByModuleSelect,
        }

    class Media:
        js = ('exams/admin/exam_module_filter.js', 'files/admin/study_file_filters.js')


@admin.register(StudyFile)
class StudyFileAdmin(admin.ModelAdmin):
    form = StudyFileAdminForm
    list_display = ('file_name', 'subcategory', 'file_type', 'file_size', 'year', 'module', 'is_trial')
    list_filter = ('year', 'module', 'subcategory', 'file_type', 'is_trial')
    search_fields = ('file_name', 'module__name')
    ordering = ('year', 'module__order', 'file_name')
    fields = ('year', 'module', 'subcategory', 'file_name', 'file_size', 'file_type', 'file_link', 'is_trial')


@admin.register(FileSubcategory)
class FileSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'order')
    list_filter = ('module__year', 'module')
    search_fields = ('name', 'module__name')
    ordering = ('module__year', 'module__order', 'order', 'name')
