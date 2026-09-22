from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Feedback, FeedbackSettings


class FeedbackSubmissionTests(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='student', email='student@example.com', password='StrongPass1',
        )
        self.client.force_login(self.student)
        self.url = reverse('feedback:submit')

    def test_student_can_submit_only_once(self):
        response = self.client.post(self.url, {'message': 'Great site!', 'hide_identity': 'on'})

        self.assertRedirects(response, self.url)
        self.assertEqual(Feedback.objects.count(), 1)
        feedback = Feedback.objects.get()
        self.assertTrue(feedback.hide_identity)
        self.assertEqual(feedback.submitter_display, 'Anonymous')

        self.client.post(self.url, {'message': 'A second response'})
        self.assertEqual(Feedback.objects.count(), 1)

    def test_deleting_feedback_allows_student_to_submit_again(self):
        Feedback.objects.create(student=self.student, message='First response')
        Feedback.objects.all().delete()

        self.client.post(self.url, {'message': 'New response'})
        self.assertEqual(Feedback.objects.count(), 1)

    def test_inactive_feedback_is_not_available(self):
        FeedbackSettings.objects.create(is_active=False)

        self.assertEqual(self.client.get(self.url).status_code, 404)
