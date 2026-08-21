from django.contrib import admin
from django.forms import ModelForm, Select

from .models import Video, VideoSubcategory


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


class VideoAdminForm(ModelForm):
    class Meta:
        model = Video
        fields = '__all__'
        widgets = {'module': ModuleByYearSelect, 'subcategory': SubcategoryByModuleSelect}

    class Media:
        js = ('exams/admin/exam_module_filter.js', 'files/admin/study_file_filters.js')


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    form = VideoAdminForm
    list_display = ('name', 'subcategory', 'year', 'module', 'is_trial')
    list_filter = ('year', 'module', 'subcategory', 'is_trial')
    search_fields = ('name', 'description', 'module__name')
    ordering = ('year', 'module__order', 'name')
    fields = ('year', 'module', 'subcategory', 'name', 'description', 'link', 'is_trial')


@admin.register(VideoSubcategory)
class VideoSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'order')
    list_filter = ('module__year', 'module')
    search_fields = ('name', 'module__name')
    ordering = ('module__year', 'module__order', 'order', 'name')
