from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_default_badges(apps, schema_editor):
    Badge = apps.get_model('progress', 'Badge')
    Badge.objects.bulk_create([
        Badge(
            name='Perfect Score', color='#d97706',
            image_url='https://api.iconify.design/solar:cup-star-bold.svg?color=%23d97706',
            xp_reward=10, rule_type='exam_score', threshold=100,
        ),
        Badge(
            name='High Achiever', color='#7c3aed',
            image_url='https://api.iconify.design/solar:medal-star-bold.svg?color=%237c3aed',
            xp_reward=5, rule_type='exam_score', threshold=80,
        ),
        Badge(
            name='Week Warrior', color='#ea580c',
            image_url='https://api.iconify.design/solar:fire-bold.svg?color=%23ea580c',
            xp_reward=10, rule_type='login_streak', threshold=7,
        ),
    ])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('progress', '0003_rank'),
    ]

    operations = [
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('color', models.CharField(default='#7c3aed', help_text='CSS color, for example #7c3aed.', max_length=20)),
                ('image_url', models.URLField(help_text='Public URL of the badge image.')),
                ('xp_reward', models.PositiveIntegerField(default=0)),
                ('rule_type', models.CharField(choices=[('exam_score', 'Exam score'), ('login_streak', 'Daily login streak')], max_length=20)),
                ('threshold', models.PositiveIntegerField(help_text='Minimum percentage for an exam-score badge, or consecutive days for a streak badge.')),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ('name',)},
        ),
        migrations.CreateModel(
            name='DailyActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-date',)},
        ),
        migrations.CreateModel(
            name='StudentBadge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('awarded_at', models.DateTimeField(auto_now_add=True)),
                ('badge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='awards', to='progress.badge')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='badges', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-awarded_at', '-pk')},
        ),
        migrations.AddConstraint(
            model_name='dailyactivity',
            constraint=models.UniqueConstraint(fields=('student', 'date'), name='one_daily_activity_per_student'),
        ),
        migrations.AddConstraint(
            model_name='studentbadge',
            constraint=models.UniqueConstraint(fields=('student', 'badge'), name='one_badge_per_student'),
        ),
        migrations.RunPython(create_default_badges, migrations.RunPython.noop),
    ]
