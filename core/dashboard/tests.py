from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from exams.models import Exam, ExamAnswer, ExamAttempt, ExamQuestion, MCQAnswer
from modules.models import Module
from osce.models import OSCEExam
from progress.models import StudentProgress


class QuizDashboardTests(TestCase):
    def test_performance_overview_uses_first_completed_attempt(self):
        user = User.objects.create_user(
            username='performance-student', email='performance@example.com',
            password='StrongPass1', academic_year=1,
        )
        module = Module.objects.create(year=1, name='Physiology', icon_class='bx-heart')
        exam = Exam.objects.create(year=1, module=module, name='Performance quiz', exam_type='practice', time_limit=20)
        first_question = ExamQuestion.objects.create(exam=exam, text='First question', order=1)
        second_question = ExamQuestion.objects.create(exam=exam, text='Second question', order=2)
        correct_answer = MCQAnswer.objects.create(question=first_question, text='Correct', is_correct=True)
        incorrect_answer = MCQAnswer.objects.create(question=second_question, text='Incorrect', is_correct=False)
        first_attempt = ExamAttempt.objects.create(exam=exam, student=user, score=1, total_questions=2)
        ExamAnswer.objects.create(attempt=first_attempt, question=first_question, selected_answer=correct_answer)
        ExamAnswer.objects.create(attempt=first_attempt, question=second_question, selected_answer=incorrect_answer)

        # A later retry must not change the first-attempt overview.
        retry = ExamAttempt.objects.create(exam=exam, student=user, score=2, total_questions=2)
        ExamAnswer.objects.create(attempt=retry, question=first_question, selected_answer=correct_answer)
        ExamAnswer.objects.create(attempt=retry, question=second_question, selected_answer=correct_answer)
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        overview = response.context['performance_overview']
        self.assertEqual(overview['correct'], 1)
        self.assertEqual(overview['incorrect'], 1)
        self.assertEqual(overview['unattempted'], 0)
        self.assertEqual(overview['accuracy'], 50)
        self.assertContains(response, '50%')

    def test_progress_leaderboard_shows_top_ten_by_xp_with_average_scores(self):
        users = []
        for number in range(11):
            user = User.objects.create_user(
                username=f'student-{number}', email=f'student-{number}@example.com', password='StrongPass1'
            )
            StudentProgress.objects.create(student=user, total_points=number * 10)
            users.append(user)

        module = Module.objects.create(year=1, name='Anatomy', icon_class='bx-heart')
        exam = Exam.objects.create(year=1, module=module, name='Quiz', exam_type='practice', time_limit=20)
        ExamAttempt.objects.create(exam=exam, student=users[10], score=4, total_questions=5)
        self.client.force_login(users[10])

        response = self.client.get(reverse('home'))
        leaderboard = response.context['leaderboard']

        self.assertEqual(len(leaderboard), 10)
        self.assertEqual([entry['xp'] for entry in leaderboard], list(range(100, 0, -10)))
        self.assertEqual(leaderboard[0]['name'], 'student-10')
        self.assertEqual(leaderboard[0]['average_score'], 80)
        self.assertContains(response, 'Top 10 students by XP')

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
