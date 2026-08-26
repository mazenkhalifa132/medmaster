from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.validators import RegexValidator
from django.db import models


class Module(models.Model):
    YEAR_CHOICES = tuple((year, f'Year {year}') for year in range(1, 6))

    year = models.PositiveSmallIntegerField(
        choices=YEAR_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    name = models.CharField(max_length=100)
    image_url = models.URLField(help_text='Public URL of the module icon image.')
    color = models.CharField(max_length=7, default='#3b82f6')
    bg_color = models.CharField(max_length=7, default='#eff6ff')
    btn_color = models.CharField(
        max_length=7,
        default='#3b82f6',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color, for example #3b82f6.')],
        verbose_name='Button color',
    )
    order = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)
    sections_count = models.PositiveSmallIntegerField(default=4)
    has_lessons = models.BooleanField(default=False, verbose_name='Lessons section')
    has_videos = models.BooleanField(default=False, verbose_name='Videos section')
    has_files = models.BooleanField(default=False, verbose_name='Files section')
    has_text = models.BooleanField(default=False, verbose_name='Text section')
    has_exams = models.BooleanField(default=True, verbose_name='Exams section')
    has_osce = models.BooleanField(default=False, verbose_name='OSCE section')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['year', 'order', 'name']
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'

    def __str__(self):
        return f"Year {self.year}: {self.name}"

    @property
    def colored_image_url(self):
        """Return the icon URL with the module color encoded as its color query parameter."""
        url_parts = urlsplit(self.image_url)
        query = [(key, value) for key, value in parse_qsl(url_parts.query) if key != 'color']
        query.append(('color', self.color))
        return urlunsplit((*url_parts[:3], urlencode(query), url_parts.fragment))
