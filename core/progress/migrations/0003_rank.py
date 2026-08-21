# Generated manually to add configurable dashboard ranks.

from django.db import migrations, models
from django.db.models import F, Q


def create_default_ranks(apps, schema_editor):
    Rank = apps.get_model('progress', 'Rank')
    Rank.objects.bulk_create([
        Rank(name='Bronze I', min_points=0, max_points=100, color='#cd7f32'),
        Rank(name='Bronze II', min_points=100, max_points=250, color='#cd7f32'),
        Rank(name='Bronze III', min_points=250, max_points=500, color='#cd7f32'),
        Rank(name='Silver I', min_points=500, max_points=800, color='#94a3b8'),
        Rank(name='Silver II', min_points=800, max_points=1200, color='#94a3b8'),
        Rank(name='Silver III', min_points=1200, max_points=1600, color='#94a3b8'),
        Rank(name='Gold I', min_points=1600, max_points=2100, color='#d4a017', icon_class='bxs-crown'),
        Rank(name='Gold II', min_points=2100, max_points=2700, color='#d4a017', icon_class='bxs-crown'),
        Rank(name='Gold III', min_points=2700, max_points=3400, color='#d4a017', icon_class='bxs-crown'),
        Rank(name='Platinum I', min_points=3400, max_points=4200, color='#7c3aed', icon_class='bxs-diamond'),
        Rank(name='Platinum II', min_points=4200, max_points=5000, color='#7c3aed', icon_class='bxs-diamond'),
        Rank(name='Platinum III', min_points=5000, max_points=6000, color='#7c3aed', icon_class='bxs-diamond'),
        Rank(name='Master', min_points=6000, max_points=8000, color='#dc2626', icon_class='bxs-medal'),
    ])


def remove_default_ranks(apps, schema_editor):
    apps.get_model('progress', 'Rank').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0002_backfill_attempt_points'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rank',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('min_points', models.PositiveIntegerField(help_text='Inclusive lower limit for this rank.')),
                ('max_points', models.PositiveIntegerField(help_text='Exclusive upper limit for this rank.')),
                ('color', models.CharField(default='#d4a017', help_text='CSS color, for example #d4a017.', max_length=20)),
                ('icon_class', models.CharField(blank=True, help_text='Optional Boxicons class, for example bxs-crown. Leave blank for no icon.', max_length=100)),
            ],
            options={
                'ordering': ('min_points', 'pk'),
            },
        ),
        migrations.AddConstraint(
            model_name='rank',
            constraint=models.CheckConstraint(condition=Q(max_points__gt=F('min_points')), name='rank_max_points_gt_min_points'),
        ),
        migrations.RunPython(create_default_ranks, remove_default_ranks),
    ]
