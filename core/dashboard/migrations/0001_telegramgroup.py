from django.db import migrations, models


def create_default_groups(apps, schema_editor):
    TelegramGroup = apps.get_model('dashboard', 'TelegramGroup')
    for year in range(1, 6):
        TelegramGroup.objects.get_or_create(year=year, defaults={'handle': 'medmaster012'})


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TelegramGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(choices=[(1, 'Year 1'), (2, 'Year 2'), (3, 'Year 3'), (4, 'Year 4'), (5, 'Year 5')], unique=True)),
                ('handle', models.CharField(default='medmaster012', help_text='Public Telegram handle, without @ or the t.me/ prefix.', max_length=128)),
            ],
            options={
                'verbose_name': 'Telegram group',
                'verbose_name_plural': 'Telegram groups',
                'ordering': ('year',),
            },
        ),
        migrations.RunPython(create_default_groups, migrations.RunPython.noop),
    ]
