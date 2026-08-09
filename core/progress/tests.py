from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import PointTransaction, StudentProgress
from .services import record_answer_points


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
