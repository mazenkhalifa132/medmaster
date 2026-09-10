from django.test import SimpleTestCase, TestCase

from .bulk_import import BulkQuestionImportError, parse_questions
from .models import Exam
from modules.models import Module


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
