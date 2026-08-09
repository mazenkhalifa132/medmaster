import csv
from io import StringIO


class BulkQuestionImportError(ValueError):
    """Raised when pasted question rows do not match the supported format."""


def parse_questions(raw_text):
    """Parse comma-separated MCQ rows into question, answer, and explanation data.

    Each non-empty row must contain six columns: question, four possible answers,
    and explanation. Empty answer columns are omitted. A trailing ``+`` marks the
    correct answer.
    """
    try:
        rows = csv.reader(StringIO(raw_text))
        parsed_rows = []
        for line_number, row in enumerate(rows, start=1):
            if not row or not any(value.strip() for value in row):
                continue

            if len(row) != 6:
                raise BulkQuestionImportError(
                    f'Line {line_number}: expected 6 comma-separated values '
                    '(question, 4 answers, explanation).'
                )

            question_text, *answer_values, explanation = (
                value.strip() for value in row
            )
            question_text = question_text.lstrip('\ufeff')
            if not question_text:
                raise BulkQuestionImportError(
                    f'Line {line_number}: the question cannot be empty.'
                )

            answers = []
            correct_answers = 0
            for answer_value in answer_values:
                if not answer_value:
                    continue
                is_correct = answer_value.endswith('+')
                answer_text = answer_value[:-1].rstrip() if is_correct else answer_value
                if not answer_text:
                    raise BulkQuestionImportError(
                        f'Line {line_number}: an answer marked with + needs text.'
                    )
                correct_answers += is_correct
                answers.append({'text': answer_text, 'is_correct': is_correct})

            if correct_answers != 1:
                raise BulkQuestionImportError(
                    f'Line {line_number}: exactly one non-empty answer must end with +.'
                )

            parsed_rows.append({
                'text': question_text,
                'answers': answers,
                'explanation': explanation,
            })
    except csv.Error as error:
        raise BulkQuestionImportError(f'Invalid CSV data: {error}') from error

    if not parsed_rows:
        raise BulkQuestionImportError('Paste at least one question row.')
    return parsed_rows
