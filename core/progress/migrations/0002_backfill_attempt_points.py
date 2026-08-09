from collections import defaultdict

from django.db import migrations


def backfill_attempt_points(apps, schema_editor):
    PointTransaction = apps.get_model('progress', 'PointTransaction')
    StudentProgress = apps.get_model('progress', 'StudentProgress')
    ExamAnswer = apps.get_model('exams', 'ExamAnswer')
    OSCEAnswerRecord = apps.get_model('osce', 'OSCEAnswerRecord')
    OSCEAttempt = apps.get_model('osce', 'OSCEAttempt')

    totals = defaultdict(lambda: [0, 0, 0])  # points, correct, incorrect

    def add_transaction(student_id, source_key, source_label, is_correct):
        points = 2 if is_correct else -1
        _, created = PointTransaction.objects.get_or_create(
            source_key=source_key,
            defaults={
                'student_id': student_id,
                'source_label': source_label,
                'points': points,
                'is_correct': is_correct,
            },
        )
        if created:
            totals[student_id][0] += points
            totals[student_id][1 if is_correct else 2] += 1

    for answer in ExamAnswer.objects.exclude(selected_answer__isnull=True).select_related(
        'attempt__exam', 'question', 'selected_answer'
    ):
        add_transaction(
            answer.attempt.student_id,
            f'exam-answer:{answer.attempt_id}:{answer.question_id}',
            f'{answer.attempt.exam.name} — question {answer.question.order}',
            answer.selected_answer.is_correct,
        )

    for answer in OSCEAnswerRecord.objects.exclude(selected_answer__isnull=True).select_related(
        'attempt__exam', 'question', 'selected_answer'
    ):
        add_transaction(
            answer.attempt.student_id,
            f'osce-mcq:{answer.attempt_id}:{answer.question_id}',
            f'{answer.attempt.exam.name} — MCQ {answer.question.order}',
            answer.selected_answer.is_correct,
        )

    for attempt in OSCEAttempt.objects.exclude(exam__osce_station='none').select_related('exam'):
        add_transaction(
            attempt.student_id,
            f'osce-station:{attempt.pk}',
            f'{attempt.exam.name} — {attempt.exam.get_osce_station_display()} station',
            attempt.practical_score == attempt.practical_total == 1,
        )

    for student_id, (points, correct, incorrect) in totals.items():
        progress, _ = StudentProgress.objects.get_or_create(student_id=student_id)
        progress.total_points += points
        progress.correct_answers += correct
        progress.incorrect_answers += incorrect
        progress.save(update_fields=('total_points', 'correct_answers', 'incorrect_answers', 'updated_at'))


class Migration(migrations.Migration):
    dependencies = [
        ('progress', '0001_initial'),
        ('exams', '0008_examanswer_text_answer'),
        ('osce', '0006_osceattempt_practical_grades'),
    ]

    operations = [
        migrations.RunPython(backfill_attempt_points, migrations.RunPython.noop),
    ]
