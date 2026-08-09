from django.contrib import admin

from .models import PointTransaction, StudentProgress


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'total_points', 'correct_answers', 'incorrect_answers', 'questions_answered', 'updated_at')
    search_fields = ('student__username', 'student__email')
    readonly_fields = ('student', 'total_points', 'correct_answers', 'incorrect_answers', 'updated_at')

    @admin.display(description='Questions answered')
    def questions_answered(self, obj):
        return obj.questions_answered


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ('student', 'points', 'is_correct', 'source_label', 'created_at')
    list_filter = ('is_correct', 'created_at')
    search_fields = ('student__username', 'student__email', 'source_label', 'source_key')
    readonly_fields = ('student', 'source_key', 'source_label', 'points', 'is_correct', 'created_at')
