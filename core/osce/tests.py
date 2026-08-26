from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from modules.models import Module

from .models import OSCEAnswer, OSCEExam, OSCEQuestion


class OSCEExamStationFieldsTests(SimpleTestCase):
    def test_bp_station_requires_both_pressures(self):
        exam = OSCEExam(osce_station='bp', systolic_pressure=120)

        with self.assertRaises(ValidationError) as error:
            exam.clean()

        self.assertIn('diastolic_pressure', error.exception.message_dict)

    def test_bp_station_requires_systolic_to_exceed_diastolic(self):
        exam = OSCEExam(
            osce_station='bp',
            systolic_pressure=80,
            diastolic_pressure=80,
        )

        with self.assertRaises(ValidationError) as error:
            exam.clean()

        self.assertIn('systolic_pressure', error.exception.message_dict)

    def test_none_station_clears_station_specific_values(self):
        exam = OSCEExam(
            osce_station='none',
            systolic_pressure=120,
            diastolic_pressure=80,
            ecg_v1=True,
            ecg_v6=True,
        )

        exam.clean()

        self.assertIsNone(exam.systolic_pressure)
        self.assertIsNone(exam.diastolic_pressure)
        self.assertFalse(exam.ecg_v1)
        self.assertFalse(exam.ecg_v6)


class OSCEViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='student',
            email='student@example.com',
            password='StrongPass123',
        )
        self.module = Module.objects.create(year=1, name='Cardiology', image_url='https://example.com/cardiology.svg')
        self.exam = OSCEExam.objects.create(
            year=1,
            module=self.module,
            name='Cardiovascular OSCE',
            retry_times=1,
            mcq_timer=20,
            osce_station='bp',
            systolic_pressure=120,
            diastolic_pressure=80,
        )
        self.question = OSCEQuestion.objects.create(exam=self.exam, question='Where is the stethoscope placed?', order=1)
        self.correct_answer = OSCEAnswer.objects.create(question=self.question, text='Over the brachial artery', is_correct=True, order=1)
        OSCEAnswer.objects.create(question=self.question, text='Over the radial artery', order=2)

    def test_detail_view_renders_osce_page(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('osce-detail', kwargs={'pk': self.exam.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertIn('Cardiovascular OSCE', response.content.decode())
        self.assertEqual(response.context['attempt_id'], response.context['attempt'].pk)

    def test_detail_view_serializes_model_questions_for_the_mcq_flow(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('osce-detail', kwargs={'pk': self.exam.pk}))

        content = response.content.decode()
        self.assertIn('id="osce-questions"', content)
        self.assertIn('Where is the stethoscope placed?', content)
        self.assertIn('Reveal answers now', content)
        self.assertIn('name="question_${question.id}"', content)

    def test_detail_view_uses_django_osce_template(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('osce-detail', kwargs={'pk': self.exam.pk}))

        self.assertTemplateUsed(response, 'osce/osce.html')

    def test_admin_bulk_import_creates_osce_questions_and_answers(self):
        admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='StrongPass123',
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse('admin:osce_osceexam_bulk_upload', args=(self.exam.pk,)),
            {
                'questions': (
                    'Which artery is assessed for a BP reading?,'
                    'Brachial artery+,Radial artery,Carotid artery,Femoral artery,'
                    'Use the brachial artery.\n'
                    'A second question,Correct answer+,Wrong answer,,,Explanation'
                ),
            },
        )

        self.assertRedirects(response, reverse('admin:osce_osceexam_change', args=(self.exam.pk,)))
        imported_questions = self.exam.questions.filter(question__in=[
            'Which artery is assessed for a BP reading?', 'A second question',
        ])
        self.assertEqual(imported_questions.count(), 2)
        self.assertEqual(imported_questions[0].answers.filter(is_correct=True).count(), 1)
        self.assertEqual(imported_questions[1].answers.filter(is_correct=True).count(), 1)

    def test_submit_view_records_mcq_answers(self):
        self.client.force_login(self.user)
        detail_response = self.client.get(reverse('osce-detail', kwargs={'pk': self.exam.pk}))
        attempt_id = detail_response.context['attempt'].pk

        response = self.client.post(
            reverse('osce-submit', kwargs={'pk': self.exam.pk}),
            {
                'attempt_id': attempt_id,
                'practical_passed': 'on',
                'practical_details': 'Completed successfully',
                f'question_{self.question.pk}': self.correct_answer.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'OSCE submitted')
        self.assertEqual(response.context['attempt'].mcq_score, 1)

    def test_submit_view_renders_station_details_as_safe_markup(self):
        self.client.force_login(self.user)
        attempt_id = self.client.get(reverse('osce-detail', kwargs={'pk': self.exam.pk})).context['attempt'].pk

        response = self.client.post(
            reverse('osce-submit', kwargs={'pk': self.exam.pk}),
            {
                'attempt_id': attempt_id,
                'practical_details': '<small class="text-muted d-block">ECG precordial lead placement</small><strong>2 / 2 leads correctly placed</strong><script>alert(1)</script>',
            },
        )

        self.assertContains(response, '<small class="text-muted d-block">ECG precordial lead placement</small>', html=True)
        self.assertContains(response, '<strong>2 / 2 leads correctly placed</strong>', html=True)
        self.assertNotContains(response, '<script>')

    def test_submit_view_renders_html_escaped_station_details_as_markup(self):
        self.client.force_login(self.user)
        attempt_id = self.client.get(reverse('osce-detail', kwargs={'pk': self.exam.pk})).context['attempt'].pk

        response = self.client.post(
            reverse('osce-submit', kwargs={'pk': self.exam.pk}),
            {
                'attempt_id': attempt_id,
                'practical_details': '&lt;small class=&quot;text-muted d-block&quot;&gt;ECG precordial lead placement&lt;/small&gt;&lt;strong&gt;2 / 2 leads correctly placed&lt;/strong&gt;',
            },
        )

        self.assertContains(response, '<small class="text-muted d-block">ECG precordial lead placement</small>', html=True)
        self.assertContains(response, '<strong>2 / 2 leads correctly placed</strong>', html=True)
