from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .admin import ExamAdminForm
from .bulk_import import BulkQuestionImportError, parse_questions
from .models import Exam, ExamQuestion, MCQAnswer
from modules.models import Module, ModuleExamSubject, ModuleExamWeek
from progress.models import PointTransaction, StudentProgress
from websitesettings.models import WebsiteSettings


class ExamOrderingTests(TestCase):
    def test_exams_are_ordered_by_order_then_name(self):
        module = Module.objects.create(
            year=1,
            name='Anatomy',
            image_url='https://example.com/anatomy.png',
        )
        later_exam = Exam.objects.create(
            year=1,
            module=module,
            name='First by name',
            order=2,
            time_limit=20,
        )
        first_exam = Exam.objects.create(
            year=1,
            module=module,
            name='Second by name',
            order=1,
            time_limit=20,
        )

        self.assertEqual(list(module.exams.all()), [first_exam, later_exam])


class ExamAdminFormTests(TestCase):
    def test_dependent_select_options_include_their_parent_ids(self):
        first_module = Module.objects.create(
            year=1, name='Anatomy', image_url='https://example.com/anatomy.png'
        )
        second_module = Module.objects.create(
            year=2, name='Physiology', image_url='https://example.com/physiology.png'
        )
        subject = ModuleExamSubject.objects.create(module=first_module, name='Upper limb')
        week = ModuleExamWeek.objects.create(module=second_module, name='Week 1')

        form_html = ExamAdminForm().as_p()

        self.assertIn(f'value="{first_module.pk}" data-year="1"', form_html)
        self.assertIn(f'value="{second_module.pk}" data-year="2"', form_html)
        self.assertIn(f'value="{subject.pk}" data-module="{first_module.pk}"', form_html)
        self.assertIn(f'value="{week.pk}" data-module="{second_module.pk}"', form_html)


class ExamFirstAttemptScoringTests(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username='first-attempt-student',
            email='first-attempt@example.com',
            password='StrongPass1',
            academic_year=1,
        )
        WebsiteSettings.objects.create(unlock_all_features=True, lock_all_features=False)
        module = Module.objects.create(year=1, name='Anatomy', image_url='https://example.com/anatomy.png')
        self.exam = Exam.objects.create(
            year=1, module=module, name='First attempt only', time_limit=20, retry_times=2,
        )
        question = ExamQuestion.objects.create(exam=self.exam, text='Question', order=1)
        self.correct_answer = MCQAnswer.objects.create(question=question, text='Correct', is_correct=True)
        self.wrong_answer = MCQAnswer.objects.create(question=question, text='Wrong')

    def test_retry_answers_do_not_change_points(self):
        self.client.force_login(self.student)

        first_attempt = self.client.get(reverse('exam-detail', args=(self.exam.pk,))).context['attempt_id']
        self.client.post(reverse('exam-submit', args=(self.exam.pk,)), {
            'attempt_id': first_attempt,
            f'question_{self.correct_answer.question_id}': self.correct_answer.pk,
        })
        progress_after_first = StudentProgress.objects.get(student=self.student)
        points_after_first = progress_after_first.total_points
        retry_attempt = self.client.get(reverse('exam-detail', args=(self.exam.pk,))).context['attempt_id']
        self.client.post(reverse('exam-submit', args=(self.exam.pk,)), {
            'attempt_id': retry_attempt,
            f'question_{self.wrong_answer.question_id}': self.wrong_answer.pk,
        })

        progress = StudentProgress.objects.get(student=self.student)
        self.assertEqual(progress.total_points, points_after_first)
        self.assertEqual(progress.correct_answers, 1)
        self.assertEqual(progress.incorrect_answers, 0)
        self.assertEqual(
            PointTransaction.objects.filter(student=self.student, source_key__startswith='exam-answer:').count(), 1
        )


class BulkQuestionParserTests(SimpleTestCase):
    def test_marks_correct_answer_and_omits_blank_answers_and_explanation(self):
        rows = parse_questions(
            'What is the normal pH?,7.35-7.45+,7.45-7.55,,,'
        )

        self.assertEqual(rows, [{
            'text': 'What is the normal pH?',
            'answers': [
                {'text': '7.35-7.45', 'is_correct': True},
                {'text': '7.45-7.55', 'is_correct': False},
            ],
            'explanation': '',
        }])

    def test_requires_exactly_one_correct_answer(self):
        with self.assertRaisesMessage(BulkQuestionImportError, 'exactly one'):
            parse_questions('Question,Answer 1,Answer 2,Answer 3,Answer 4,')
