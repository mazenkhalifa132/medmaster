from django.db import models


def normalize_phone(phone):
    return ''.join(character for character in (phone or '') if character.isdigit())


class StudentVerification(models.Model):
    """Phone-based entitlement for content in a student's assigned year."""

    YEAR_CHOICES = tuple((year, f'Year {year}') for year in range(1, 6))

    phone = models.CharField(max_length=20, unique=True)
    activation_year = models.PositiveSmallIntegerField(
        choices=YEAR_CHOICES,
        blank=True,
        null=True,
        help_text='Select the academic year this activation unlocks.',
    )
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('phone',)
        verbose_name = 'Student verification'
        verbose_name_plural = 'Student verifications'

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.phone} ({"active" if self.is_active else "inactive"})'
