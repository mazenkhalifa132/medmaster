from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings

from modules.models import Module


class Exam(models.Model):
    YEAR_CHOICES = tuple((year, f'Year {year}') for year in range(1, 6))
    EXAM_TYPE_CHOICES = (
        ('practice', 'Practice'),
        ('mid', 'Mid'),
        ('finale', 'Finale'),
        ('ospe', 'OSPE'),
        ('saq', 'SAQ'),
    )

    year = models.PositiveSmallIntegerField(
        choices=YEAR_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=200)
    exam_type = models.CharField(
        max_length=10,
        choices=EXAM_TYPE_CHOICES,
        default='practice',
    )
    time_limit = models.PositiveIntegerField(
        help_text='Time allowed for the exam, in minutes.'
    )
    retry_times = models.PositiveSmallIntegerField(
        default=0,
        help_text='Total number of attempts allowed for each student.',
    )
    is_trial = models.BooleanField(default=False, help_text='Make this exam available to every authenticated student.')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('year', 'module__order', 'name')
        constraints = [
            models.UniqueConstraint(
                fields=('module', 'name'), name='unique_exam_name_per_module'
            )
        ]

    def clean(self):
        super().clean()
        if self.module_id and self.year != self.module.year:
            raise ValidationError({'module': 'The module must belong to the selected exam year.'})

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def result(self):
        """Default result before an attempt is made."""
        return f'0/{self.question_count}'

    def __str__(self):
        return f'Year {self.year} - {self.module.name}: {self.name} ({self.get_exam_type_display()})'


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    image_url = models.URLField(blank=True, verbose_name='Image link')
    answer_explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('order', 'pk')

    def __str__(self):
        return f'{self.exam.name} - Question {self.order}'


class MCQAnswer(models.Model):
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('order', 'pk')

    def clean(self):
        super().clean()
        if self.is_correct and self.question_id:
            other_correct_answer_exists = self.question.answers.exclude(pk=self.pk).filter(
                is_correct=True
            ).exists()
            if other_correct_answer_exists:
                raise ValidationError({'is_correct': 'Only one answer can be marked correct.'})

    def __str__(self):
        return self.text


class ExamAttempt(models.Model):
    """A completed exam attempt belonging to one student."""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-submitted_at',)

    @property
    def result(self):
        return f'{self.score}/{self.total_questions}'

    def __str__(self):
        return f'{self.student} - {self.exam}: {self.result}'


class ExamAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(MCQAnswer, on_delete=models.SET_NULL, blank=True, null=True)
    text_answer = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('attempt', 'question'), name='one_answer_per_attempt_question')
        ]
