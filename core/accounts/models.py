import re

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class UserManager(DjangoUserManager):
    def _validate_password_strength(self, password):
        if not password:
            return

        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')

        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one number.')

    def create_user(self, username, email=None, password=None, **extra_fields):
        if password is None:
            raise ValueError('Password is required.')
        self._validate_password_strength(password)
        return super().create_user(username, email=email, password=password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if password is None:
            raise ValueError('Password is required.')
        self._validate_password_strength(password)
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    BAN_NONE = 'none'
    BAN_TEMPORARY = 'temporary'
    BAN_PERMANENT = 'permanent'
    BAN_CHOICES = (
        (BAN_NONE, 'Not banned'),
        (BAN_TEMPORARY, 'Temporary'),
        (BAN_PERMANENT, 'Permanent'),
    )

    ROLE_CHOICES = (
        ('student', 'Student'),
        ('admin', 'Admin'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True, default=None)
    academic_year = models.PositiveSmallIntegerField(blank=True, null=True)
    academic_year_change_used = models.BooleanField(
        default=False,
        help_text='Whether the student has already used their one profile academic-year change.',
    )
    name_change_used = models.BooleanField(
        default=False,
        help_text='Whether the student has already used their one name change.',
    )
    email = models.EmailField(unique=True)
    ban_type = models.CharField(max_length=12, choices=BAN_CHOICES, default=BAN_NONE)
    banned_until = models.DateTimeField(
        blank=True, null=True,
        help_text='Required for a temporary ban. The ban ends automatically at this time.',
    )
    ban_reason = models.CharField(max_length=255, blank=True)

    objects = UserManager()

    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_banned(self):
        if self.ban_type == self.BAN_PERMANENT:
            return True
        return (
            self.ban_type == self.BAN_TEMPORARY
            and self.banned_until is not None
            and self.banned_until > timezone.now()
        )

    def clean(self):
        super().clean()
        if self.ban_type == self.BAN_TEMPORARY and not self.banned_until:
            raise ValidationError({'banned_until': 'Set an end date and time for a temporary ban.'})
        if self.ban_type != self.BAN_TEMPORARY:
            self.banned_until = None
        if self.ban_type == self.BAN_NONE:
            self.ban_reason = ''
        password = self.password
        if password and not password.startswith('pbkdf2_sha256$'):
            self.validate_password_strength(password)

    def validate_password_strength(self, password):
        if not password:
            return

        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')

        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')

        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')

        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one number.')

    def save(self, *args, **kwargs):
        if self.role == 'admin' and not self.is_staff:
            self.is_staff = True
        elif self.role != 'admin' and self.is_staff and not self.is_superuser:
            self.is_staff = False

        raw_password = self.password
        if raw_password and not raw_password.startswith('pbkdf2_sha256$'):
            self.set_password(raw_password)

        super().save(*args, **kwargs)
