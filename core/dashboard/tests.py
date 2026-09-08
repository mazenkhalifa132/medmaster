from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exams.models import Exam, ExamAttempt
from modules.models import Module
from osce.models import OSCEAttempt, OSCEExam
from progress.models import Badge, StudentBadge, StudentProgress


class QuizDashboardTests(TestCase):
    def test_earned_badge_exposes_modal_details(self):
        user = User.objects.create_user(
            username='badge-student', email='badge-student@example.com', password='StrongPass1', academic_year=1,
        )
        badge = Badge.objects.create(
            name='Quiz Master', description='Earn this by achieving an excellent quiz score.',
            image_url='https://example.com/badge.svg', xp_reward=25,
            rule_type=Badge.EXAM_SCORE, threshold=80,
        )
        StudentBadge.objects.create(student=user, badge=badge, source_key='badge-test')
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.context['badge_progress'][0].points_earned, 25)
        self.assertContains(response, 'data-badge-description="Earn this by achieving an excellent quiz score."')
        self.assertContains(response, 'id="badgeDetailModal"')

    def test_score_cards_show_highest_and_latest_completed_attempts(self):
        user = User.objects.create_user(
            username='score-student', email='score-student@example.com', password='StrongPass1', academic_year=1,
        )
        module = Module.objects.create(year=1, name='Scoring', image_url='https://example.com/scoring.svg')
        quiz = Exam.objects.create(year=1, module=module, name='Quiz', exam_type='practice', time_limit=20)
        osce = OSCEExam.objects.create(
            year=1, module=module, name='OSCE', mcq_timer=20, osce_station='bp',
        )
        older_attempt = ExamAttempt.objects.create(exam=quiz, student=user, score=9, total_questions=10)
        older_attempt.submitted_at = timezone.now() - timedelta(days=1)
        older_attempt.save(update_fields=('submitted_at',))
        OSCEAttempt.objects.create(
            exam=osce, student=user, mcq_score=2, total_questions=4, practical_score=1, practical_total=1,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.context['highest_score'], 90)
        self.assertEqual(response.context['latest_score'], 60)
        self.assertContains(response, '90%')
        self.assertContains(response, '60%')

    def test_progress_leaderboard_shows_top_ten_by_xp_with_average_scores(self):
        users = []
        for number in range(11):
            user = User.objects.create_user(
                username=f'student-{number}', email=f'student-{number}@example.com', password='StrongPass1'
            )
            StudentProgress.objects.create(student=user, total_points=number * 10)
            users.append(user)
        admin = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='StrongPass1', role='admin'
        )
        StudentProgress.objects.create(student=admin, total_points=1000)

        module = Module.objects.create(year=1, name='Anatomy', image_url='https://example.com/anatomy.svg')
        exam = Exam.objects.create(year=1, module=module, name='Quiz', exam_type='practice', time_limit=20)
        ExamAttempt.objects.create(exam=exam, student=users[10], score=4, total_questions=5)
        self.client.force_login(users[10])

        response = self.client.get(reverse('home'))
        leaderboard = response.context['leaderboard']

        self.assertEqual(len(leaderboard), 10)
        self.assertEqual([entry['xp'] for entry in leaderboard], list(range(100, 0, -10)))
        self.assertEqual(leaderboard[0]['name'], 'student-10')
        self.assertEqual(leaderboard[0]['average_score'], 80)
        self.assertNotIn(admin.pk, [entry['student_id'] for entry in leaderboard])
        self.assertContains(response, 'Top 10 students by Points')

    def test_dashboard_serializes_database_quizzes_with_retries(self):
        user = User.objects.create_user(
            username='student', email='student@example.com', password='StrongPass1'
        )
        module = Module.objects.create(year=1, name='Anatomy', image_url='https://example.com/anatomy.svg')
        exam = Exam.objects.create(
            year=1, module=module, name='Upper limb quiz', exam_type='practice',
            time_limit=20, retry_times=3,
        )
        ExamAttempt.objects.create(exam=exam, student=user, score=1, total_questions=5)
        ExamAttempt.objects.create(exam=exam, student=user, score=5, total_questions=5)
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'quizzes-by-year-data')
        self.assertContains(response, 'Upper limb quiz')
        self.assertContains(response, '"retries": 1')
        self.assertContains(response, '"score": "20%"')

    def test_dashboard_serializes_osce_exams_for_card_display(self):
        user = User.objects.create_user(
            username='osce-student', email='osce@example.com', password='StrongPass1'
        )
        module = Module.objects.create(year=1, name='Clinical skills', image_url='https://example.com/clinical-skills.svg')
        OSCEExam.objects.create(
            year=1, module=module, name='Cardiovascular OSCE', retry_times=2,
            mcq_timer=600, osce_station='bp',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'osce-exams-by-year-data')
        self.assertContains(response, 'Cardiovascular OSCE')
        self.assertContains(response, '"station": "bp"')
