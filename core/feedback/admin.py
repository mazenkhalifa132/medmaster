from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .models import Feedback, FeedbackSettings


@admin.register(FeedbackSettings)
class FeedbackSettingsAdmin(admin.ModelAdmin):
    fields = ('is_active',)

    def has_add_permission(self, request):
        return not FeedbackSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('submitter', 'hide_identity', 'created_at', 'short_message')
    list_filter = ('hide_identity', 'created_at')
    search_fields = ('message', 'student__username', 'student__first_name', 'student__last_name')
    readonly_fields = ('student', 'message', 'hide_identity', 'created_at')
    actions = ('delete_selected_feedback',)
    change_list_template = 'admin/feedback/feedback/change_list.html'

    def has_add_permission(self, request):
        return False

    @admin.display(description='Student')
    def submitter(self, obj):
        return obj.submitter_display

    @admin.display(description='Feedback')
    def short_message(self, obj):
        return obj.message[:100]

    @admin.action(description='Delete selected feedback')
    def delete_selected_feedback(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} feedback item(s) deleted.', messages.SUCCESS)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download/', self.admin_site.admin_view(self.download_feedback), name='feedback_feedback_download'),
            path('delete-all/', self.admin_site.admin_view(self.delete_all_feedback), name='feedback_feedback_delete_all'),
        ]
        return custom_urls + urls

    def download_feedback(self, request):
        lines = []
        for feedback in Feedback.objects.select_related('student').all():
            lines.extend((
                f'Date: {feedback.created_at:%Y-%m-%d %H:%M UTC}',
                f'Student: {feedback.submitter_display}',
                f'Feedback: {feedback.message}',
                '-' * 72,
            ))
        response = HttpResponse('\n'.join(lines) or 'No feedback submitted yet.\n', content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="feedback.txt"'
        return response

    def delete_all_feedback(self, request):
        if request.method == 'POST':
            count, _ = Feedback.objects.all().delete()
            self.message_user(request, f'All feedback deleted ({count} item(s)). Students can submit feedback again.', messages.SUCCESS)
            return redirect(reverse('admin:feedback_feedback_changelist'))
        context = {
            **self.admin_site.each_context(request),
            'title': 'Delete all feedback',
            'feedback_count': Feedback.objects.count(),
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/feedback/feedback/delete_all_confirmation.html', context)
