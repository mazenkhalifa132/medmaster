from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def default_expiry():
    return timezone.now() + timedelta(hours=48)


class Notification(models.Model):
    CONTENT = 'content'
    BADGE = 'badge'
    ANNOUNCEMENT = 'announcement'
    KIND_CHOICES = (
        (CONTENT, 'New learning content'),
        (BADGE, 'Badge earned'),
        (ANNOUNCEMENT, 'Announcement'),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    url = models.CharField(max_length=500, blank=True)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)
    seen_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at', '-pk')
        indexes = [models.Index(fields=('recipient', 'seen_at', 'expires_at'))]

    @property
    def is_active(self):
        return self.seen_at is None and self.expires_at > timezone.now()

    def mark_seen(self):
        if self.seen_at is None:
            self.seen_at = timezone.now()
            self.save(update_fields=('seen_at',))

    def __str__(self):
        return f'{self.recipient}: {self.title}'


class NotificationBroadcast(models.Model):
    """Staff-created announcement delivered to every active user."""

    title = models.CharField(max_length=255)
    message = models.TextField()
    url = models.CharField(max_length=500, blank=True, help_text='Optional destination path or URL.')
    expires_at = models.DateTimeField(default=default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_notification_broadcasts',
    )

    class Meta:
        ordering = ('-created_at', '-pk')
        verbose_name = 'Notification broadcast'
        verbose_name_plural = 'Notification broadcasts'

    def __str__(self):
        return self.title
