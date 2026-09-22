from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'academic_year', 'role', 'is_staff', 'is_active')
    list_filter = ('academic_year', 'role', 'is_staff', 'is_active')
    list_editable = ('academic_year',)
    list_display_links = ('username', 'email')
    ordering = ('academic_year', 'username')
    search_fields = ('username', 'email', 'first_name', 'last_name')
