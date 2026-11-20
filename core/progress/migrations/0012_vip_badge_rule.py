from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0011_badge_exams'),
    ]

    operations = [
        migrations.AlterField(
            model_name='badge',
            name='rule_type',
            field=models.CharField(
                choices=[
                    ('exam_score', 'Exam score'),
                    ('module_progress', 'Module progress'),
                    ('login_streak', 'Daily login streak'),
                    ('vip_badge', 'VIP Badge'),
                ],
                max_length=20,
            ),
        ),
    ]
