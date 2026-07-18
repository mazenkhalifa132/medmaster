from django.core.exceptions import ValidationError
from django.db import models

from modules.models import Module


class StudyFile(models.Model):
    FILE_TYPE_CHOICES = (
        ('pdf', 'PDF'),
        ('word', 'Word'),
        ('powerpoint', 'PowerPoint'),
    )

    year = models.PositiveSmallIntegerField(choices=Module.YEAR_CHOICES)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='study_files')
    file_name = models.CharField(max_length=255)
    file_size = models.CharField(max_length=20, help_text='For example: 2.4 MB')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_link = models.URLField()

    class Meta:
        ordering = ('year', 'module__order', 'file_name')
        verbose_name = 'Study file'
        verbose_name_plural = 'Study files'

    def clean(self):
        super().clean()
        if self.module_id and self.year != self.module.year:
            raise ValidationError({'module': 'The module must belong to the selected year.'})

    def __str__(self):
        return f'Year {self.year} - {self.module.name}: {self.file_name}'
