from django.contrib import admin
from .models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'year', 'order', 'has_lessons', 'has_videos', 'has_files', 'has_text',
        'has_exams', 'has_osce', 'is_active',
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
            'fields': ('icon_class', 'color', 'bg_color', 'btn_color', 'sections_count'),
        }),
    )
