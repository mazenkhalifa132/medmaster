from django.contrib import admin
from django.contrib import messages

from .models import StudentVerification
from .services import assign_activated_academic_years, notify_activated_students


@admin.register(StudentVerification)
class StudentVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone', 'activation_year', 'is_active', 'updated_at')
    list_filter = ('activation_year', 'is_active')
    search_fields = ('phone', 'notes')
    fields = ('phone', 'activation_year', 'is_active', 'notes')
    actions = ('activate_selected', 'deactivate_selected')

    @admin.action(description='Activate selected phone numbers')
    def activate_selected(self, request, queryset):
        activations = list(queryset.exclude(activation_year__isnull=True))
        activated = len(activations)
        if activations:
            newly_activated = [activation for activation in activations if not activation.is_active]
            StudentVerification.objects.filter(pk__in=[activation.pk for activation in activations]).update(is_active=True)
            for activation in activations:
                activation.is_active = True
            assigned = assign_activated_academic_years(activations)
            notified = notify_activated_students(newly_activated)
        else:
            assigned = 0
            notified = 0
        missing_year = queryset.filter(activation_year__isnull=True).count()
        if activated:
            self.message_user(
                request,
                f'{activated} activation(s) enabled; {assigned} student academic year(s) assigned; '
                f'{notified} activation notification(s) sent.',
                messages.SUCCESS,
            )
        if missing_year:
            self.message_user(
                request,
                f'{missing_year} record(s) were not activated because an activation year is required.',
                messages.WARNING,
            )

    @admin.action(description='Deactivate selected phone numbers')
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)
