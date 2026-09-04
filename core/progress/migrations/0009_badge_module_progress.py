import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0007_module_button_color_palette'),
        ('progress', '0008_badge_exam'),
    ]

    operations = [
        migrations.AddField(
            model_name='badge',
            name='module',
            field=models.ForeignKey(
                blank=True,
                help_text='Module required for a module-progress badge.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='progress_badges',
                to='modules.module',
            ),
        ),
        migrations.AlterField(
            model_name='badge',
            name='rule_type',
            field=models.CharField(
                choices=[
                    ('exam_score', 'Exam score'),
                    ('module_progress', 'Module progress'),
                    ('login_streak', 'Daily login streak'),
                ],
                max_length=20,
            ),
        ),
    ]
