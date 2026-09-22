from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class WebsiteSettings(models.Model):
    """The single, site-wide access mode configured by an administrator."""

    unlock_all_features = models.BooleanField(
        default=False,
        help_text='Give every authenticated user access to all learning content.',
    )
    lock_all_features = models.BooleanField(
        default=True,
        help_text='Restrict unactivated users to trial content only.',
    )
    correct_answer_points = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Points awarded for each correct answer on an exam first attempt.',
    )
    wrong_answers_per_deduction = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        help_text='Apply a deduction after this many incorrect answers on exam first attempts.',
    )
    wrong_answer_deduction = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Points deducted whenever the incorrect-answer threshold is reached.',
    )

    class Meta:
        verbose_name = 'website settings'
        verbose_name_plural = 'website settings'

    @property
    def all_features_unlocked(self):
        # Unlocking takes priority so an administrator cannot accidentally
        # leave the site locked after enabling the global override.
        return self.unlock_all_features

    def clean(self):
        super().clean()
        if self.unlock_all_features == self.lock_all_features:
            raise ValidationError(
                'Select exactly one access mode: unlock all features or lock all features.'
            )

    @classmethod
    def all_features_are_unlocked(cls):
        settings = cls.objects.order_by('pk').first()
        return bool(settings and settings.all_features_unlocked)

    def __str__(self):
        return 'Website access settings'
