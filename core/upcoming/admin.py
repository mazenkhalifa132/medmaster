from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from django.db import models

from .models import UpcomingEvent


@admin.register(UpcomingEvent)
class UpcomingEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'scheduled_at', 'icon')
    list_filter = ('scheduled_at',)
    search_fields = ('title',)
    ordering = ('scheduled_at',)
    formfield_overrides = {
        models.DateTimeField: {'widget': AdminSplitDateTime},
    }
