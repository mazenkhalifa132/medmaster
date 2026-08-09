from django.conf import settings
from django.db import models

from modules.models import Module


class Note(models.Model):
    """A private study note owned by one student."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    year = models.PositiveSmallIntegerField(
        choices=Module.YEAR_CHOICES,
        blank=True,
        null=True,
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.SET_NULL,
        related_name='notes',
        blank=True,
        null=True,
    )
    color = models.CharField(max_length=7, editable=False, default='#3b82f6')
    title = models.CharField(max_length=200)
    date = models.DateTimeField(auto_now_add=True)
    content = models.TextField()

    class Meta:
        ordering = ('-date',)
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'

    def __str__(self):
        return f'{self.student} — {self.title}'

    def save(self, *args, **kwargs):
        if self.module_id:
            self.year = self.module.year
            self.color = self.module.color
        super().save(*args, **kwargs)
