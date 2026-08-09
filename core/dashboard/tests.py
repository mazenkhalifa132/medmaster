from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from exams.models import Exam, ExamAttempt
from modules.models import Module
from osce.models import OSCEExam


class QuizDashboardTests(TestCase):
    def test_dashboard_serializes_database_quizzes_with_retries(self):
        user = User.objects.create_user(
            username='student', email='student@example.com', password='StrongPass1'
        )
        module = Module.objects.create(year=1, name='Anatomy', icon_class='bx-heart')
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
        module = Module.objects.create(year=1, name='Clinical skills', icon_class='bx-first-aid')
        OSCEExam.objects.create(
            year=1, module=module, name='Cardiovascular OSCE', retry_times=2,
            mcq_timer=600, osce_station='bp',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'osce-exams-by-year-data')
        self.assertContains(response, 'Cardiovascular OSCE')
        self.assertContains(response, '"station": "bp"')
