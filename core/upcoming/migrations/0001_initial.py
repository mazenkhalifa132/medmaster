# Generated manually for the UpcomingEvent model.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='UpcomingEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icon', models.CharField(default='bx-calendar-event', help_text='Boxicons icon class, for example: bx-edit or bx-first-aid.', max_length=100)),
                ('title', models.CharField(max_length=200)),
                ('scheduled_at', models.DateTimeField(verbose_name='date and time')),
            ],
            options={
                'verbose_name': 'upcoming event',
                'verbose_name_plural': 'upcoming events',
                'ordering': ('scheduled_at',),
            },
        ),
    ]
