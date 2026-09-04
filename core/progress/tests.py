from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from exams.models import Exam, ExamAttempt
from modules.models import Module
from .models import Badge, PointTransaction, Rank, StudentBadge, StudentProgress, StudentWeeklyGoal, WeeklyGoal
from .services import (
    award_exam_badges, award_module_progress_badges, evaluate_weekly_goals,
    record_answer_points, weekly_goal_progress,
)


class RankIconUrlTests(TestCase):
    def test_rank_icon_uses_the_selected_rank_color(self):
        rank = Rank(
            name='Bronze',
            min_points=0,
            max_points=100,
            color='#d97706',
            image_url='https://api.iconify.design/bi/bell-fill.svg?color=%23000000',
        )

        self.assertEqual(
            rank.colored_image_url,
            'https://api.iconify.design/bi/bell-fill.svg?color=%23d97706',
        )

    def test_badge_icon_uses_the_selected_badge_color(self):
        badge = Badge(
            name='High scorer', color='#0ea5e9', image_url='https://api.iconify.design/solar:medal-star-bold.svg',
            rule_type=Badge.EXAM_SCORE, threshold=80,
        )

        self.assertEqual(
            badge.colored_image_url,
            'https://api.iconify.design/solar:medal-star-bold.svg?color=%230ea5e9',
        )


class ExamBadgeTests(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(username='badge-student', password='SafePassword1!')
        module = Module.objects.create(year=1, name='Anatomy', image_url='https://example.com/anatomy.svg')
        self.target_exam = Exam.objects.create(year=1, module=module, name='Target quiz', time_limit=20)
        self.other_exam = Exam.objects.create(year=1, module=module, name='Other quiz', time_limit=20)
        self.global_badge = Badge.objects.create(
            name='Global high score', image_url='https://example.com/global.svg',
            rule_type=Badge.EXAM_SCORE, threshold=80,
        )
        self.target_badge = Badge.objects.create(
            name='Target high score', image_url='https://example.com/target.svg', exam=self.target_exam,
            rule_type=Badge.EXAM_SCORE, threshold=80,
        )

    def test_exam_badge_is_awarded_only_for_its_selected_exam(self):
        award_exam_badges(
            student=self.student, score=9, total_questions=10, attempt_key='exam:other', exam=self.other_exam,
        )
        awarded_badge_ids = set(StudentBadge.objects.values_list('badge_id', flat=True))
        self.assertIn(self.global_badge.pk, awarded_badge_ids)
        self.assertNotIn(self.target_badge.pk, awarded_badge_ids)

        award_exam_badges(
            student=self.student, score=9, total_questions=10, attempt_key='exam:target', exam=self.target_exam,
        )
        awarded_badge_ids = set(StudentBadge.objects.values_list('badge_id', flat=True))
        self.assertIn(self.global_badge.pk, awarded_badge_ids)
        self.assertIn(self.target_badge.pk, awarded_badge_ids)

    def test_module_progress_badge_uses_combined_first_attempt_scores(self):
        module_badge = Badge.objects.create(
            name='Anatomy progress', image_url='https://example.com/module.svg',
            rule_type=Badge.MODULE_PROGRESS, module=self.target_exam.module, threshold=80,
        )
        retry_badge = Badge.objects.create(
            name='Anatomy perfection', image_url='https://example.com/module-perfect.svg',
            rule_type=Badge.MODULE_PROGRESS, module=self.target_exam.module, threshold=90,
        )
        ExamAttempt.objects.create(exam=self.target_exam, student=self.student, score=8, total_questions=10)
        ExamAttempt.objects.create(exam=self.other_exam, student=self.student, score=9, total_questions=10)
        # Retries do not improve the module-progress result.
        ExamAttempt.objects.create(exam=self.target_exam, student=self.student, score=10, total_questions=10)

        award_module_progress_badges(student=self.student, module=self.target_exam.module)

        self.assertTrue(StudentBadge.objects.filter(badge=module_badge, student=self.student).exists())
        self.assertFalse(StudentBadge.objects.filter(badge=retry_badge, student=self.student).exists())


class AdminLeaderboardTests(TestCase):
    def test_admin_leaderboard_lists_only_students_in_score_order(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='StrongPass1', role='admin',
        )
        first_student = User.objects.create_user(
            username='first', email='first@example.com', phone='01000000001', password='StrongPass1',
        )
        second_student = User.objects.create_user(
            username='second', email='second@example.com', phone='01000000002', password='StrongPass1',
        )
        module = Module.objects.create(year=1, name='Anatomy', image_url='https://example.com/anatomy.svg')
        exam = Exam.objects.create(year=1, module=module, name='Quiz', time_limit=20)
        ExamAttempt.objects.create(exam=exam, student=first_student, score=8, total_questions=10)
        ExamAttempt.objects.create(exam=exam, student=second_student, score=6, total_questions=10)
        ExamAttempt.objects.create(exam=exam, student=admin_user, score=10, total_questions=10)

        self.client.force_login(admin_user)
        response = self.client.get(reverse('admin:progress_studentprogress_leaderboard'))

        self.assertEqual(response.status_code, 200)
        leaderboard = response.context['leaderboard']
        self.assertEqual([entry['student'] for entry in leaderboard], [first_student, second_student])
        self.assertEqual(leaderboard[0]['percentage'], 80)
        self.assertEqual(leaderboard[0]['total_points'], 0)
        self.assertEqual(leaderboard[0]['correct_answers'], 0)
        self.assertEqual(leaderboard[0]['incorrect_answers'], 0)


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
