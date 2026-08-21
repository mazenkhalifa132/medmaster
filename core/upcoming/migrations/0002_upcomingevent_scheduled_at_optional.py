from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upcoming', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='upcomingevent',
            name='scheduled_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Leave blank to show this event as “Coming soon”.',
                null=True,
                verbose_name='date and time',
            ),
        ),
    ]
