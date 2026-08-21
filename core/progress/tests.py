from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from exams.models import Exam, ExamAttempt
from modules.models import Module
from .models import PointTransaction, StudentProgress, StudentWeeklyGoal, WeeklyGoal
from .services import evaluate_weekly_goals, record_answer_points, weekly_goal_progress


class PointScoringTests(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='points-student', password='SafePassword1!'
        )

    def test_correct_and_incorrect_answers_update_the_total(self):
        record_answer_points(
            student=self.student,
            source_key='exam-answer:1:1',
            source_label='Anatomy — question 1',
            is_correct=True,
        )
        record_answer_points(
            student=self.student,
            source_key='exam-answer:1:2',
            source_label='Anatomy — question 2',
            is_correct=False,
        )

        progress = StudentProgress.objects.get(student=self.student)
        self.assertEqual(progress.total_points, 1)
        self.assertEqual(progress.correct_answers, 1)
        self.assertEqual(progress.incorrect_answers, 1)
        self.assertEqual(progress.questions_answered, 2)

    def test_same_answer_cannot_be_scored_twice(self):
        kwargs = {
            'student': self.student,
            'source_key': 'osce-station:1',
            'source_label': 'BP station',
            'is_correct': True,
        }
        self.assertTrue(record_answer_points(**kwargs))
        self.assertFalse(record_answer_points(**kwargs))

        self.assertEqual(StudentProgress.objects.get(student=self.student).total_points, 2)
        self.assertEqual(PointTransaction.objects.count(), 1)

    def test_questions_solved_goal_awards_xp_once_when_reached(self):
        WeeklyGoal.objects.create(
            name='Question sprint',
            start_date=timezone.localdate(),
            goal_type=WeeklyGoal.QUESTIONS_SOLVED,
            target=2,
            xp_reward=10,
        )

        attempt = self._completed_exam_attempt()
        record_answer_points(
            student=self.student, source_key=f'exam-answer:{attempt.pk}:1', source_label='Quiz question 1', is_correct=True,
        )
        record_answer_points(
            student=self.student, source_key=f'exam-answer:{attempt.pk}:2', source_label='Quiz question 2', is_correct=False,
        )
        evaluate_weekly_goals(student=self.student)

        progress = StudentProgress.objects.get(student=self.student)
        self.assertEqual(progress.total_points, 11)
        self.assertEqual(StudentWeeklyGoal.objects.count(), 1)
        self.assertEqual(PointTransaction.objects.filter(source_key__startswith='weekly-goal:').count(), 1)

    def test_max_incorrect_goal_only_awards_after_week_ends(self):
        goal = WeeklyGoal.objects.create(
            name='Accuracy week',
            start_date=timezone.localdate() - timedelta(days=7),
            goal_type=WeeklyGoal.MAX_INCORRECT_ANSWERS,
            target=1,
            xp_reward=8,
        )

        attempt = self._completed_exam_attempt()
        record_answer_points(
            student=self.student,
            source_key=f'exam-answer:{attempt.pk}:1',
            source_label='Quiz question 1',
            is_correct=False,
        )
        PointTransaction.objects.filter(source_key=f'exam-answer:{attempt.pk}:1').update(
            created_at=timezone.make_aware(datetime.combine(goal.start_date, time.min))
        )
        evaluate_weekly_goals(student=self.student)

        self.assertEqual(StudentWeeklyGoal.objects.filter(goal=goal).count(), 1)
        self.assertEqual(PointTransaction.objects.filter(source_key__startswith='weekly-goal:').count(), 1)

    def test_weekly_goal_ignores_answers_from_exam_retries(self):
        goal = WeeklyGoal.objects.create(
            name='First try sprint',
            start_date=timezone.localdate(),
            goal_type=WeeklyGoal.QUESTIONS_SOLVED,
            target=2,
            xp_reward=10,
        )
        first_attempt = self._completed_exam_attempt()
        retry_attempt = self._completed_exam_attempt(exam=first_attempt.exam)
        record_answer_points(
            student=self.student, source_key=f'exam-answer:{first_attempt.pk}:1',
            source_label='First try question', is_correct=True,
        )
        record_answer_points(
            student=self.student, source_key=f'exam-answer:{retry_attempt.pk}:1',
            source_label='Retry question 1', is_correct=True,
        )
        record_answer_points(
            student=self.student, source_key=f'exam-answer:{retry_attempt.pk}:2',
            source_label='Retry question 2', is_correct=True,
        )

        progress = weekly_goal_progress(student=self.student, goal=goal)

        self.assertEqual(progress['current'], 1)
        self.assertFalse(progress['completed'])
        self.assertFalse(StudentWeeklyGoal.objects.filter(goal=goal).exists())

    def _completed_exam_attempt(self, exam=None):
        if exam is None:
            module = Module.objects.create(year=1, name='Anatomy')
            exam = Exam.objects.create(
                year=1,
                module=module,
                name='Weekly goal quiz',
                exam_type='practice',
                time_limit=20,
                retry_times=2,
            )
        return ExamAttempt.objects.create(
            exam=exam,
            student=self.student,
            score=1,
            total_questions=1,
        )
