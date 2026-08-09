from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'year', 'module', 'date')
    list_filter = ('year', 'module', 'date')
    search_fields = ('title', 'content', 'student__username', 'student__email')
    readonly_fields = ('color', 'date')
    ordering = ('-date',)
