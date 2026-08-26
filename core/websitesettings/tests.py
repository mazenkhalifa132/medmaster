from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from verification.services import has_year_access

from .models import WebsiteSettings


class WebsiteSettingsAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student', email='student@example.com', password='StrongPass1', academic_year=1
        )

    def test_unactivated_student_is_locked_by_default(self):
        self.assertFalse(has_year_access(self.student, 1))

    def test_unlock_all_features_grants_access_to_unactivated_students(self):
        WebsiteSettings.objects.create(unlock_all_features=True, lock_all_features=False)

        self.assertTrue(has_year_access(self.student, 1))

    def test_exactly_one_access_mode_must_be_selected(self):
        with self.assertRaises(ValidationError):
            WebsiteSettings(unlock_all_features=True, lock_all_features=True).full_clean()

        with self.assertRaises(ValidationError):
            WebsiteSettings(unlock_all_features=False, lock_all_features=False).full_clean()
