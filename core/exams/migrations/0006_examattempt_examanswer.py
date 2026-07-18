from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exams', '0005_alter_exam_exam_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveIntegerField(default=0)),
                ('total_questions', models.PositiveIntegerField(default=0)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='exams.exam')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-submitted_at',)},
        ),
        migrations.CreateModel(
            name='ExamAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='exams.examattempt')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='exams.examquestion')),
                ('selected_answer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='exams.mcqanswer')),
            ],
        ),
        migrations.AddConstraint(model_name='examanswer', constraint=models.UniqueConstraint(fields=('attempt', 'question'), name='one_answer_per_attempt_question')),
    ]
