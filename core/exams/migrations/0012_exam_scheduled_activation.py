from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0011_exam_subject_exam_week'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='auto_activate',
            field=models.BooleanField(
                default=False,
                help_text='Automatically make this exam active on the selected date.',
                verbose_name='Auto activate by date',
            ),
        ),
        migrations.AddField(
            model_name='exam',
            name='activation_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
