from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0012_exam_scheduled_activation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamActivationAnnouncement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_attempt_at', models.DateTimeField(blank=True, null=True)),
                ('attempt_count', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('exam', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='activation_announcement', to='exams.exam')),
            ],
            options={
                'verbose_name': 'exam activation announcement',
                'verbose_name_plural': 'exam activation announcements',
            },
        ),
    ]
