from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from modules.models import Module


class VideoSubcategory(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='video_subcategories')
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ('module__year', 'module__order', 'order', 'name')
        constraints = [
            models.UniqueConstraint(
                fields=('module', 'name'),
                name='unique_video_subcategory_name_per_module',
            )
        ]
        verbose_name = 'Video subcategory'
        verbose_name_plural = 'Video subcategories'

    def __str__(self):
        return f'{self.module.name}: {self.name}'


class Video(models.Model):
    year = models.PositiveSmallIntegerField(choices=Module.YEAR_CHOICES)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='videos')
    subcategory = models.ForeignKey(
        VideoSubcategory,
        on_delete=models.SET_NULL,
        related_name='videos',
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    link = models.URLField(help_text='Paste a YouTube or embeddable video link.')
    is_trial = models.BooleanField(default=False, help_text='Make this video available to every authenticated student.')

    class Meta:
        ordering = ('year', 'module__order', 'name')
        verbose_name = 'Video'
        verbose_name_plural = 'Videos'

    def clean(self):
        super().clean()
        if self.module_id and self.year != self.module.year:
            raise ValidationError({'module': 'The module must belong to the selected year.'})
        if self.subcategory_id and self.subcategory.module_id != self.module_id:
            raise ValidationError({'subcategory': 'The subcategory must belong to the selected module.'})

    @property
    def embed_url(self):
        """Convert common YouTube share links to a URL that can be embedded."""
        parsed = urlparse(self.link)
        video_id = None
        if parsed.netloc in ('youtu.be', 'www.youtu.be'):
            video_id = parsed.path.strip('/').split('/')[0]
        elif parsed.netloc in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
            if parsed.path == '/watch':
                video_id = parse_qs(parsed.query).get('v', [None])[0]
            elif parsed.path.startswith('/embed/'):
                return self.link
        if video_id:
            return f'https://www.youtube.com/embed/{video_id}'
        return self.link

    def __str__(self):
        return f'Year {self.year} - {self.module.name}: {self.name}'


class VideoWatch(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_watches')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='watches')
    watched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('student', 'video'), name='unique_video_watch_per_student')
        ]
        verbose_name = 'Video watch'
        verbose_name_plural = 'Video watches'

    def __str__(self):
        return f'{self.student} watched {self.video}'
