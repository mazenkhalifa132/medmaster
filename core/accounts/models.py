import re

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.db import models


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
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('admin', 'Admin'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True, default=None)
    academic_year = models.PositiveSmallIntegerField(blank=True, null=True)
    email = models.EmailField(unique=True)

    objects = UserManager()

    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    def clean(self):
        super().clean()
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
