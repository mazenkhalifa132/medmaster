from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('progress', '0005_repeatable_badges'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeeklyGoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('start_date', models.DateField(help_text='The goal runs for seven days starting on this date.')),
                ('goal_type', models.CharField(choices=[('questions_solved', 'Questions solved'), ('correct_answers', 'Correct answers'), ('max_incorrect_answers', 'Maximum incorrect answers')], max_length=30)),
                ('target', models.PositiveIntegerField(help_text='Required count, or the maximum wrong answers allowed.')),
                ('xp_reward', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ('-start_date', '-pk')},
        ),
        migrations.CreateModel(
            name='StudentWeeklyGoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('awarded_at', models.DateTimeField(auto_now_add=True)),
                ('goal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='awards', to='progress.weeklygoal')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_goal_awards', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-awarded_at', '-pk')},
        ),
        migrations.AddConstraint(
            model_name='weeklygoal',
            constraint=models.UniqueConstraint(fields=('start_date',), name='one_weekly_goal_per_start_date'),
        ),
        migrations.AddConstraint(
            model_name='studentweeklygoal',
            constraint=models.UniqueConstraint(fields=('student', 'goal'), name='one_weekly_goal_award_per_student'),
        ),
    ]
