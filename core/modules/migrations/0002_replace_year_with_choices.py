from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


def delete_existing_years(apps, schema_editor):
    """Remove the old Year records and their dependent modules."""
    Year = apps.get_model('modules', 'Year')
    Year.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(delete_existing_years, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='module',
            name='year',
        ),
        migrations.DeleteModel(
            name='Year',
        ),
        migrations.AddField(
            model_name='module',
            name='year',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Year 1'), (2, 'Year 2'), (3, 'Year 3'), (4, 'Year 4'), (5, 'Year 5')],
                default=1,
                validators=[MinValueValidator(1), MaxValueValidator(5)],
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='module',
            options={
                'ordering': ['year', 'order', 'name'],
                'verbose_name': 'Module',
                'verbose_name_plural': 'Modules',
            },
        ),
    ]
