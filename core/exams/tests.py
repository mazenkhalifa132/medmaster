from django.test import SimpleTestCase

from .bulk_import import BulkQuestionImportError, parse_questions


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
