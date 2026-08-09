from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from modules.models import Module

User = get_user_model()


class OSCEExam(models.Model):
    """An OSCE exam and its MCQ content."""

    YEAR_CHOICES = tuple((year, f'Year {year}') for year in range(1, 6))
    STATION_CHOICES = (
        ('bp', 'BP'),
        ('ecg', 'Ecg'),
        ('none', 'None'),
    )

    year = models.PositiveSmallIntegerField(
        choices=YEAR_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='osce_exams',
    )
    name = models.CharField(max_length=200)
    retry_times = models.PositiveSmallIntegerField(
        default=0,
        help_text='Total number of attempts allowed for each student.',
    )
    mcq_timer = models.PositiveIntegerField(
        help_text='Time allowed for the MCQ section, in minutes.',
    )
    osce_station = models.CharField(
        max_length=4,
        choices=STATION_CHOICES,
        default='none',
    )
    systolic_pressure = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text='Systolic blood pressure in mmHg.',
    )
    diastolic_pressure = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text='Diastolic blood pressure in mmHg.',
    )
    ecg_v1 = models.BooleanField('V1', default=False)
    ecg_v2 = models.BooleanField('V2', default=False)
    ecg_v3 = models.BooleanField('V3', default=False)
    ecg_v4 = models.BooleanField('V4', default=False)
    ecg_v5 = models.BooleanField('V5', default=False)
    ecg_v6 = models.BooleanField('V6', default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('year', 'module__order', 'name')
        constraints = [
            models.UniqueConstraint(
                fields=('module', 'name'),
                name='unique_osce_exam_name_per_module',
            )
        ]

    def clean(self):
        super().clean()
        if self.module_id and self.year != self.module.year:
            raise ValidationError(
                {'module': 'The module must belong to the selected exam year.'}
            )

        if self.osce_station == 'bp':
            if self.systolic_pressure is None:
                raise ValidationError({'systolic_pressure': 'Enter the systolic pressure for a BP station.'})
            if self.diastolic_pressure is None:
                raise ValidationError({'diastolic_pressure': 'Enter the diastolic pressure for a BP station.'})
            if (
                self.systolic_pressure is not None
                and self.diastolic_pressure is not None
                and self.systolic_pressure <= self.diastolic_pressure
            ):
                raise ValidationError({'systolic_pressure': 'Systolic pressure must be greater than diastolic pressure.'})
        else:
            self.systolic_pressure = None
            self.diastolic_pressure = None

        if self.osce_station != 'ecg':
            self.ecg_v1 = False
            self.ecg_v2 = False
            self.ecg_v3 = False
            self.ecg_v4 = False
            self.ecg_v5 = False
            self.ecg_v6 = False

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def graded_question_count(self):
        """MCQs plus the practical station, when this OSCE has one."""
        return self.question_count + (1 if self.osce_station != 'none' else 0)

    def __str__(self):
        return f'Year {self.year} - {self.module.name}: {self.name}'


class OSCEQuestion(models.Model):
    exam = models.ForeignKey(OSCEExam, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    image_link = models.URLField(blank=True)
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('order', 'pk')

    def __str__(self):
        return f'{self.exam.name} - Question {self.order}'


class OSCEAnswer(models.Model):
    question = models.ForeignKey(
        OSCEQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('order', 'pk')

    def clean(self):
        super().clean()
        if self.is_correct and self.question_id:
            another_correct_answer = self.question.answers.exclude(pk=self.pk).filter(
                is_correct=True
            ).exists()
            if another_correct_answer:
                raise ValidationError({'is_correct': 'Only one answer can be marked correct.'})

    def __str__(self):
        return self.text


class OSCEAttempt(models.Model):
    exam = models.ForeignKey(OSCEExam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='osce_attempts')
    practical_passed = models.BooleanField(default=False)
    practical_details = models.TextField(blank=True)
    practical_score = models.PositiveSmallIntegerField(default=0)
    practical_total = models.PositiveSmallIntegerField(default=0)
    mcq_score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-submitted_at', 'pk')

    @property
    def result(self):
        if self.total_questions == 0:
            return '0/0'
        return f'{self.mcq_score}/{self.total_questions}'

    @property
    def practical_result(self):
        return f'{self.practical_score}/{self.practical_total}' if self.practical_total else 'N/A'

    @property
    def total_score(self):
        return self.practical_score + self.mcq_score

    @property
    def total_possible_score(self):
        # A practical station is always one graded item, in addition to the
        # exam's MCQs. This keeps historical attempts and new attempts alike
        # on the same total-grade scale.
        return self.exam.graded_question_count

    @property
    def grade_result(self):
        return f'{self.total_score}/{self.total_possible_score}' if self.total_possible_score else '0/0'

    def __str__(self):
        return f'{self.student} - {self.exam.name}'


class OSCEAnswerRecord(models.Model):
    attempt = models.ForeignKey(OSCEAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(OSCEQuestion, on_delete=models.CASCADE, related_name='answer_records')
    selected_answer = models.ForeignKey(OSCEAnswer, on_delete=models.SET_NULL, null=True, blank=True, related_name='selected_in_attempts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('question__order', 'question__pk')

    def __str__(self):
        return f'{self.attempt} - {self.question}'
