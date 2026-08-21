from django.core.exceptions import ValidationError
from django.db import models

from modules.models import Module


class FileSubcategory(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='file_subcategories')
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ('module__year', 'module__order', 'order', 'name')
        constraints = [
            models.UniqueConstraint(
                fields=('module', 'name'),
                name='unique_file_subcategory_name_per_module',
            )
        ]
        verbose_name = 'File subcategory'
        verbose_name_plural = 'File subcategories'

    def __str__(self):
        return f'{self.module.name}: {self.name}'


class StudyFile(models.Model):
    FILE_TYPE_CHOICES = (
        ('pdf', 'PDF'),
        ('word', 'Word'),
        ('powerpoint', 'PowerPoint'),
    )

    year = models.PositiveSmallIntegerField(choices=Module.YEAR_CHOICES)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='study_files')
    subcategory = models.ForeignKey(
        FileSubcategory,
        on_delete=models.SET_NULL,
        related_name='study_files',
        blank=True,
        null=True,
    )
    file_name = models.CharField(max_length=255)
    file_size = models.CharField(max_length=20, help_text='For example: 2.4 MB')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_link = models.URLField()
    is_trial = models.BooleanField(default=False, help_text='Make this file available to every authenticated student.')

    class Meta:
        ordering = ('year', 'module__order', 'file_name')
        verbose_name = 'Study file'
        verbose_name_plural = 'Study files'

    def clean(self):
        super().clean()
        if self.module_id and self.year != self.module.year:
            raise ValidationError({'module': 'The module must belong to the selected year.'})
        if self.subcategory_id and self.subcategory.module_id != self.module_id:
            raise ValidationError({'subcategory': 'The subcategory must belong to the selected module.'})

    def __str__(self):
        return f'Year {self.year} - {self.module.name}: {self.file_name}'
