from django.conf import settings
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


RANKS = (
    ('Bronze I', 0, 100),
    ('Bronze II', 100, 250),
    ('Bronze III', 250, 500),
    ('Silver I', 500, 800),
    ('Silver II', 800, 1200),
    ('Silver III', 1200, 1600),
    ('Gold I', 1600, 2100),
    ('Gold II', 2100, 2700),
    ('Gold III', 2700, 3400),
    ('Platinum I', 3400, 4200),
    ('Platinum II', 4200, 5000),
    ('Platinum III', 5000, 6000),
    ('Master', 6000, 8000),
)


def rank_for_points(points):
    """Return the current rank and its progress range for a points total."""
    points = max(points, 0)
    for name, minimum, next_minimum in RANKS:
        if points < next_minimum:
            return {'name': name, 'minimum': minimum, 'next': next_minimum}
    name, minimum, _ = RANKS[-1]
    return {'name': name, 'minimum': minimum, 'next': minimum + 1000}
