from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_notification_dismissed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationbroadcast',
            name='target_academic_year',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, 'All years'),
                    (1, 'Year 1'),
                    (2, 'Year 2'),
                    (3, 'Year 3'),
                    (4, 'Year 4'),
                    (5, 'Year 5'),
                ],
                default=0,
                help_text='Choose a year to notify only its students, or All years for everyone.',
                verbose_name='Audience',
            ),
        ),
    ]
