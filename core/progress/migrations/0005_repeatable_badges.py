from django.db import migrations, models


def assign_legacy_source_keys(apps, schema_editor):
    StudentBadge = apps.get_model('progress', 'StudentBadge')
    for award in StudentBadge.objects.filter(source_key__isnull=True):
        award.source_key = f'legacy-badge:{award.pk}'
        award.save(update_fields=('source_key',))


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0004_badge_system'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentbadge',
            name='source_key',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RunPython(assign_legacy_source_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='studentbadge',
            name='source_key',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.RemoveConstraint(
            model_name='studentbadge',
            name='one_badge_per_student',
        ),
    ]
