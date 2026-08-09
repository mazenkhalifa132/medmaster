from django.db import models


class UpcomingEvent(models.Model):
    """An event shown in the Upcoming panel."""

    icon = models.CharField(
        max_length=100,
        default='bx-calendar-event',
        help_text='Boxicons icon class, for example: bx-edit or bx-first-aid.',
    )
    title = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField('date and time')

    class Meta:
        ordering = ('scheduled_at',)
        verbose_name = 'upcoming event'
        verbose_name_plural = 'upcoming events'

    def __str__(self):
        return f'{self.title} - {self.scheduled_at:%b %d, %Y %I:%M %p}'
