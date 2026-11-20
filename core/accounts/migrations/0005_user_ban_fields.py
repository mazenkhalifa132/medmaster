from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_academic_year_change_used'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='ban_type',
            field=models.CharField(
                choices=[('none', 'Not banned'), ('temporary', 'Temporary'), ('permanent', 'Permanent')],
                default='none',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='banned_until',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Required for a temporary ban. The ban ends automatically at this time.',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='ban_reason',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
