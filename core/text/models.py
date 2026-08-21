from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from modules.models import Module

from .sanitizers import sanitize_rich_text


class TextSubcategory(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='text_subcategories')
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ('module__year', 'module__order', 'order', 'name')
        constraints = [
            models.UniqueConstraint(
                fields=('module', 'name'),
                name='unique_text_subcategory_name_per_module',
            )
        ]
        verbose_name = 'Text subcategory'
        verbose_name_plural = 'Text subcategories'

    def __str__(self):
        return f'{self.module.name}: {self.name}'


class TextContent(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    title = models.CharField(max_length=255)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='text_contents')
    subcategory = models.ForeignKey(
        TextSubcategory,
        on_delete=models.SET_NULL,
        related_name='text_contents',
        blank=True,
        null=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='authored_text_contents',
        null=True,
        blank=True,
    )
    content = models.TextField(help_text='Use the visual editor to create your content.')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    is_trial = models.BooleanField(default=False, help_text='Make this text content available to every authenticated student.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('module__year', 'module__order', 'title')
        verbose_name = 'Text content'
        verbose_name_plural = 'Text content'

    def save(self, *args, **kwargs):
        self.content = sanitize_rich_text(self.content)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.subcategory_id and self.subcategory.module_id != self.module_id:
            raise ValidationError({'subcategory': 'The subcategory must belong to the selected module.'})

    def __str__(self):
        return f'{self.module}: {self.title}'


class TextContentImage(models.Model):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.FileField(
        upload_to='text-content/%Y/%m/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-uploaded_at',)
        verbose_name = 'Text content image'
        verbose_name_plural = 'Text content images'
