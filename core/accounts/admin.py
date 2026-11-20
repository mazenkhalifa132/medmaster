from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    UserChangeForm as DjangoUserChangeForm,
    UserCreationForm as DjangoUserCreationForm,
)
from .models import User


class UserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        ban_type = cleaned_data.get('ban_type')
        banned_until = cleaned_data.get('banned_until')
        if ban_type == User.BAN_TEMPORARY and not banned_until:
            self.add_error('banned_until', 'Set an end date and time for a temporary ban.')
        if ban_type != User.BAN_TEMPORARY:
            cleaned_data['banned_until'] = None
        if ban_type == User.BAN_NONE:
            cleaned_data['ban_reason'] = ''
        return cleaned_data


class UserAdminPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields.pop('usable_password', None)
        self.fields['password1'].required = True
        self.fields['password2'].required = True

    def validate_password_for_user(self, user, **kwargs):
        super().validate_password_for_user(user, **kwargs)
        password = self.cleaned_data.get('password2')
        if password:
            user.validate_password_strength(password)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = UserAdminPasswordChangeForm
    change_user_password_template = 'admin/auth/user/change_password.html'

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Academic access', {'fields': ('role', 'academic_year', 'academic_year_change_used')}),
        ('Ban', {'fields': ('ban_type', 'banned_until', 'ban_reason')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    list_display = ('username', 'email', 'academic_year', 'role', 'ban_status', 'is_staff', 'is_active')
    list_filter = ('academic_year', 'role', 'ban_type', 'is_staff', 'is_active')
    list_editable = ('academic_year',)
    list_display_links = ('username', 'email')
    ordering = ('academic_year', 'username')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')

    @admin.display(description='Ban status')
    def ban_status(self, obj):
        if obj.is_banned:
            return 'Permanent' if obj.ban_type == User.BAN_PERMANENT else 'Temporary'
        if obj.ban_type == User.BAN_TEMPORARY:
            return 'Expired'
        return 'Not banned'
