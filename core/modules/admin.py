from django.contrib import admin
from django import forms

from .models import Module, ModuleExamSubject, ModuleExamWeek


class ModuleAdminForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = '__all__'
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'aria-label': 'Module color'}),
            'bg_color': forms.TextInput(attrs={'type': 'color', 'aria-label': 'Module background color'}),
            'btn_color': forms.TextInput(attrs={'type': 'color', 'aria-label': 'Module button color'}),
        }
        labels = {
            'color': 'Icon color',
            'bg_color': 'Background color',
            'btn_color': 'Button color',
        }


class ModuleExamSubjectInline(admin.TabularInline):
    model = ModuleExamSubject
    extra = 1
    fields = ('name', 'order')


class ModuleExamWeekInline(admin.TabularInline):
    model = ModuleExamWeek
    extra = 1
    fields = ('name', 'order')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    form = ModuleAdminForm
    inlines = (ModuleExamSubjectInline, ModuleExamWeekInline)
    list_display = (
        'name', 'year', 'order', 'has_lessons', 'has_videos', 'has_files', 'has_text',
        'has_exams', 'has_osce', 'image_url', 'is_active',
    )
    list_filter = ('year', 'is_active')
    ordering = ('year', 'order', 'name')
    search_fields = ('name',)
    fieldsets = (
        (None, {'fields': ('year', 'name', 'description', 'order', 'is_active')}),
        ('Available sections', {
            'fields': ('has_lessons', 'has_videos', 'has_files', 'has_text', 'has_exams', 'has_osce'),
        }),
        ('Appearance and details', {
            'fields': ('image_url', 'color', 'bg_color', 'btn_color', 'sections_count'),
        }),
    )

    class Media:
        js = ('modules/admin/exam_section_settings.js',)
