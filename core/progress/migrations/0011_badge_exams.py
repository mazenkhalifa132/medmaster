from django.db import migrations, models


def copy_exam_attachments(apps, schema_editor):
    Badge = apps.get_model('progress', 'Badge')
    for badge in Badge.objects.exclude(exam__isnull=True).iterator():
        badge.exams.add(badge.exam_id)


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0010_badge_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='badge',
            name='exams',
            field=models.ManyToManyField(
                blank=True,
                help_text='Optional. Attach this badge to one or more exams; leave blank to award it for every exam.',
                related_name='badges',
                to='exams.exam',
            ),
        ),
        migrations.RunPython(copy_exam_attachments, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='badge',
            name='exam',
        ),
    ]
