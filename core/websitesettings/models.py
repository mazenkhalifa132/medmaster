from django.db import models
from django.core.exceptions import ValidationError


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
