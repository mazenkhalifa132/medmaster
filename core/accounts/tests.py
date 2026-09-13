from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import User
from progress.models import StudentProgress


@override_settings(
    TURNSTILE_SITE_KEY='test-site-key',
    TURNSTILE_SECRET_KEY='test-secret-key',
)
@patch('accounts.views.verify_turnstile', return_value=True)
class AuthFlowTests(TestCase):
    def test_terms_page_is_public_and_signup_links_to_it(self, _verify_turnstile):
        response = self.client.get(reverse('terms'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Terms &amp; Conditions')
        self.assertContains(response, 'MEDICAL DISCLAIMER')

        response = self.client.get(reverse('auth'))

        self.assertContains(response, f'href="{reverse("terms")}"')
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, 'data-sitekey="test-site-key"')

    def test_student_signup_and_login(self, _verify_turnstile):
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

    def test_signup_cannot_assign_admin_role(self, _verify_turnstile):
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

    def test_invalid_signup_keeps_entered_values_and_shows_signup_form(self, _verify_turnstile):
        response = self.client.post(
            reverse('signup'),
            {
                'first_name': 'Mazen',
                'last_name': 'Ahmed',
                'email': 'mazen@example.com',
                'phone': '+201000000000',
                'academic_year': '3',
                'password1': 'StrongPass123!',
                'password2': 'DifferentPass123!',
                'agree_terms': 'on',
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Passwords do not match.', status_code=400)
        self.assertContains(response, 'value="Mazen"', status_code=400)
        self.assertContains(response, 'value="mazen@example.com"', status_code=400)
        self.assertContains(response, 'value="3" selected', status_code=400)
        self.assertContains(response, 'id="signup-form" class="auth-form"', status_code=400)

    def test_admin_login_updates_last_login_without_validating_existing_phone(self, _verify_turnstile):
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

    def test_phone_must_be_unique(self, _verify_turnstile):
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

    def test_password_must_meet_strength_requirements(self, _verify_turnstile):
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='weakpass',
                email='weak@example.com',
                password='weakpass',
                role='student',
            )

    def test_logout_clears_session(self, _verify_turnstile):
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

    def test_student_profile_cannot_change_academic_year(self, _verify_turnstile):
        user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='ProfilePass123!',
            first_name='Original',
            last_name='Student',
            academic_year=1,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('profile'),
            {
                'first_name': 'Updated',
                'last_name': 'Student',
                # A forged form submission must not allow year switching.
                'academic_year': '5',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.academic_year, 1)

    def test_admin_can_delete_student_with_progress(self, _verify_turnstile):
        admin_user = User.objects.create_superuser(
            username='deleteadmin',
            email='deleteadmin@example.com',
            password='AdminPass123!',
        )
        student = User.objects.create_user(
            username='studenttodelete',
            email='studenttodelete@example.com',
            password='StudentPass123!',
            role='student',
        )
        progress = StudentProgress.objects.create(student=student, total_points=50)
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse('admin:accounts_user_delete', args=(student.pk,)),
            {'post': 'yes'},
        )

        self.assertRedirects(response, reverse('admin:accounts_user_changelist'))
        self.assertFalse(User.objects.filter(pk=student.pk).exists())
        self.assertFalse(StudentProgress.objects.filter(pk=progress.pk).exists())

    def test_signup_rejects_failed_turnstile_check(self, _verify_turnstile):
        _verify_turnstile.return_value = False

        response = self.client.post(reverse('signup'), {'first_name': 'Mazen'})

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Please complete the security check and try again.', status_code=400)
