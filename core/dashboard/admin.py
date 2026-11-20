from django.contrib import admin

from .models import TelegramGroup


@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ('year', 'handle', 'bot_chat_id')
    fields = ('year', 'handle', 'bot_chat_id')
    ordering = ('year',)
