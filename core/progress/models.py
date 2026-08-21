from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class StudentProgress(models.Model):
    """The current points summary for one student."""

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progress',
    )
    total_points = models.IntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    incorrect_answers = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'student progress'

    @property
    def questions_answered(self):
        return self.correct_answers + self.incorrect_answers

    @property
    def rank(self):
        return rank_for_points(self.total_points)

    def __str__(self):
        return f'{self.student} — {self.total_points} XP'


class PointTransaction(models.Model):
    """One awarded or deducted point event. source_key makes scoring idempotent."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_transactions',
    )
    source_key = models.CharField(max_length=100, unique=True)
    source_label = models.CharField(max_length=255)
    points = models.SmallIntegerField()
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-pk')

    def __str__(self):
        return f'{self.student}: {self.points:+d} XP — {self.source_label}'


class Rank(models.Model):
    """A configurable student rank and the points interval that earns it."""

    name = models.CharField(max_length=100, unique=True)
    min_points = models.PositiveIntegerField(help_text='Inclusive lower limit for this rank.')
    max_points = models.PositiveIntegerField(help_text='Exclusive upper limit for this rank.')
    color = models.CharField(max_length=20, default='#d4a017', help_text='CSS color, for example #d4a017.')
    icon_class = models.CharField(
        max_length=100,
        blank=True,
        help_text='Optional Boxicons class, for example bxs-crown. Leave blank for no icon.',
    )

    class Meta:
        ordering = ('min_points', 'pk')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_points__gt=models.F('min_points')),
                name='rank_max_points_gt_min_points',
            ),
        ]

    def clean(self):
        super().clean()
        if self.max_points <= self.min_points:
            raise ValidationError({'max_points': 'The maximum must be greater than the minimum.'})
        overlaps = Rank.objects.filter(min_points__lt=self.max_points, max_points__gt=self.min_points)
        if self.pk:
            overlaps = overlaps.exclude(pk=self.pk)
        if overlaps.exists():
            raise ValidationError('This points range overlaps an existing rank.')

    def __str__(self):
        return f'{self.name} ({self.min_points}–{self.max_points} XP)'


class Badge(models.Model):
    """A configurable achievement that can award XP once to each student."""

    EXAM_SCORE = 'exam_score'
    LOGIN_STREAK = 'login_streak'
    RULE_CHOICES = (
        (EXAM_SCORE, 'Exam score'),
        (LOGIN_STREAK, 'Daily login streak'),
    )

    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=20, default='#7c3aed', help_text='CSS color, for example #7c3aed.')
    image_url = models.URLField(help_text='Public URL of the badge image.')
    xp_reward = models.PositiveIntegerField(default=0)
    rule_type = models.CharField(max_length=20, choices=RULE_CHOICES)
    threshold = models.PositiveIntegerField(
        help_text='Minimum percentage for an exam-score badge, or consecutive days for a streak badge.'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.rule_type == self.EXAM_SCORE and self.threshold > 100:
            raise ValidationError({
                'threshold': 'For an exam-score badge, enter the required exam percentage (0–100).'
            })

    @property
    def threshold_requirement(self):
        if self.rule_type == self.EXAM_SCORE:
            return f'{self.threshold}% exam score'
        return f'{self.threshold} day login streak'


class StudentBadge(models.Model):
    """Records each time a student earns a badge from a qualifying event."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awards')
    source_key = models.CharField(max_length=100, unique=True)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-awarded_at', '-pk')
    def __str__(self):
        return f'{self.student} — {self.badge}'


class DailyActivity(models.Model):
    """One dashboard visit per student per day, used to calculate login streaks."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_activities')
    date = models.DateField()

    class Meta:
        ordering = ('-date',)
        constraints = [
            models.UniqueConstraint(fields=('student', 'date'), name='one_daily_activity_per_student'),
        ]


class WeeklyGoal(models.Model):
    """A seven-day, site-wide question goal configured by staff."""

    QUESTIONS_SOLVED = 'questions_solved'
    CORRECT_ANSWERS = 'correct_answers'
    MAX_INCORRECT_ANSWERS = 'max_incorrect_answers'
    GOAL_TYPE_CHOICES = (
        (QUESTIONS_SOLVED, 'Questions solved'),
        (CORRECT_ANSWERS, 'Correct answers'),
        (MAX_INCORRECT_ANSWERS, 'Maximum incorrect answers'),
    )

    name = models.CharField(max_length=100)
    start_date = models.DateField(help_text='The goal runs for seven days starting on this date.')
    goal_type = models.CharField(max_length=30, choices=GOAL_TYPE_CHOICES)
    target = models.PositiveIntegerField(help_text='Required count, or the maximum wrong answers allowed.')
    xp_reward = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-start_date', '-pk')
        constraints = [
            models.UniqueConstraint(fields=('start_date',), name='one_weekly_goal_per_start_date'),
        ]

    @property
    def end_date(self):
        from datetime import timedelta

        return self.start_date + timedelta(days=7)

    @property
    def requirement(self):
        if self.goal_type == self.QUESTIONS_SOLVED:
            return f'Solve {self.target} questions'
        if self.goal_type == self.CORRECT_ANSWERS:
            return f'Get {self.target} correct answers'
        return f'Make no more than {self.target} wrong answers'

    def __str__(self):
        return f'{self.name} ({self.start_date:%d %b %Y})'


class StudentWeeklyGoal(models.Model):
    """Records the single XP award for a student who completes a weekly goal."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weekly_goal_awards',
    )
    goal = models.ForeignKey(WeeklyGoal, on_delete=models.CASCADE, related_name='awards')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-awarded_at', '-pk')
        constraints = [
            models.UniqueConstraint(fields=('student', 'goal'), name='one_weekly_goal_award_per_student'),
        ]

    def __str__(self):
        return f'{self.student} — {self.goal}'


def rank_for_points(points):
    """Return the configured rank for a points total."""
    points = max(points, 0)
    rank = Rank.objects.filter(min_points__lte=points, max_points__gt=points).first()
    if rank:
        return rank

    # Keep awarding the highest configured rank when a student exceeds its range.
    return Rank.objects.filter(min_points__lte=points).order_by('-min_points', '-pk').first() or Rank.objects.first()
