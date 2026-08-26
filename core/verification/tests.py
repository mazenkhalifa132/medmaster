from django.test import TestCase

from accounts.models import User
from notifications.models import Notification

from .models import StudentVerification


class StudentVerificationTests(TestCase):
    def test_active_verification_assigns_its_year_to_matching_student(self):
        student = User.objects.create_user(
            username='verified-student',
            email='verified@example.com',
            password='StrongPass123!',
            phone='+20 100 000 0000',
            academic_year=1,
        )

        StudentVerification.objects.create(
            phone='201000000000',
            activation_year=4,
            is_active=True,
        )

        student.refresh_from_db()
        self.assertEqual(student.academic_year, 4)
        notification = Notification.objects.get(recipient=student)
        self.assertEqual(notification.title, 'Year 4 activated')
        self.assertIn('Year 4', notification.message)

    def test_unactivated_students_see_locked_notes_and_progress_navigation(self):
        student = User.objects.create_user(
            username='unactivated-student',
            email='unactivated@example.com',
            password='StrongPass123!',
            academic_year=1,
        )
        self.client.force_login(student)

        response = self.client.get('/')

        self.assertContains(response, 'nav-link-locked')
        self.assertContains(response, 'Notes <small class="nav-premium-label">Premium</small>')
        self.assertContains(response, 'Progress <small class="nav-premium-label">Premium</small>')

    def test_activated_student_sees_unlocked_premium_navigation(self):
        student = User.objects.create_user(
            username='activated-student',
            email='activated@example.com',
            password='StrongPass123!',
            phone='+20 100 000 0001',
            academic_year=1,
        )
        StudentVerification.objects.create(
            phone='201000000001',
            activation_year=1,
            is_active=True,
        )
        self.client.force_login(student)

        response = self.client.get('/')

        self.assertNotContains(response, 'nav-link-locked')
        self.assertContains(response, 'href="/#notes"')
        self.assertContains(response, 'href="/#progress"')
