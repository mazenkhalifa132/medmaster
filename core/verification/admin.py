from django.contrib import admin
from django.contrib import messages

from .models import StudentVerification


@admin.register(StudentVerification)
class StudentVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone', 'activation_year', 'is_active', 'updated_at')
    list_filter = ('activation_year', 'is_active')
    search_fields = ('phone', 'notes')
    fields = ('phone', 'activation_year', 'is_active', 'notes')
    actions = ('activate_selected', 'deactivate_selected')

    @admin.action(description='Activate selected phone numbers')
    def activate_selected(self, request, queryset):
        activated = queryset.exclude(activation_year__isnull=True).update(is_active=True)
        missing_year = queryset.filter(activation_year__isnull=True).count()
        if activated:
            self.message_user(request, f'{activated} activation(s) enabled.', messages.SUCCESS)
        if missing_year:
            self.message_user(
                request,
                f'{missing_year} record(s) were not activated because an activation year is required.',
                messages.WARNING,
            )

    @admin.action(description='Deactivate selected phone numbers')
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)
