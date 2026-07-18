from django.test import TestCase
from django.urls import reverse

from .models import User


class AuthFlowTests(TestCase):
    def test_student_signup_and_login(self):
        response = self.client.post(
            reverse('signup'),
            {
                'first_name': 'Mazen',
                'last_name': 'Ahmed',
                'email': 'student@example.com',
                'phone': '+201000000000',
                'academic_year': '3',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
                'agree_terms': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='student@example.com')
        self.assertEqual(user.role, 'student')
        self.assertTrue(user.check_password('StrongPass123!'))

        login_response = self.client.post(
            reverse('login'),
            {'email': 'student@example.com', 'password': 'StrongPass123!'},
        )
        self.assertEqual(login_response.status_code, 302)

    def test_signup_cannot_assign_admin_role(self):
        response = self.client.post(
            reverse('signup'),
            {
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@example.com',
                'phone': '+201111111111',
                'academic_year': '5',
                'role': 'admin',
                'password1': 'AdminPass123!',
                'password2': 'AdminPass123!',
                'agree_terms': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='admin@example.com')
        self.assertEqual(user.role, 'student')
        self.assertFalse(user.is_staff)

    def test_admin_login_updates_last_login_without_validating_existing_phone(self):
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPass123!',
            phone='+201111111111',
        )

        response = self.client.post(
            reverse('admin:login'),
            {'username': user.username, 'password': 'AdminPass123!'},
        )

        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertIsNotNone(user.last_login)

    def test_phone_must_be_unique(self):
        User.objects.create_user(
            username='firstuser',
            email='first@example.com',
            password='StrongPass123!',
            phone='+201000000000',
            role='student',
        )

        with self.assertRaises(Exception):
            User.objects.create_user(
                username='seconduser',
                email='second@example.com',
                password='StrongPass123!',
                phone='+201000000000',
                role='student',
            )

    def test_password_must_meet_strength_requirements(self):
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='weakpass',
                email='weak@example.com',
                password='weakpass',
                role='student',
            )

    def test_logout_clears_session(self):
        user = User.objects.create_user(
            username='logoutuser',
            email='logout@example.com',
            password='LogoutPass123!',
            role='student',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('logout'))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
