from django.db import models
from django.conf import settings


class FeedbackSettings(models.Model):
    """Controls whether students can access the feedback form."""

    is_active = models.BooleanField(
        default=True,
        help_text='Show the Feedback button and allow new feedback submissions.',
    )

    class Meta:
        verbose_name = 'feedback settings'
        verbose_name_plural = 'feedback settings'

    def __str__(self):
        return 'Feedback settings'


class Feedback(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback_submissions',
    )
    message = models.TextField()
    hide_identity = models.BooleanField(
        default=False,
        help_text='Do not show this student’s identity with the feedback.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(fields=('student',), name='one_feedback_per_student'),
        ]

    def __str__(self):
        return f'Feedback #{self.pk}'

    @property
    def submitter_display(self):
        if self.hide_identity:
            return 'Anonymous'
        return self.student.get_full_name() or self.student.username

# Create your models here.
