from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_ban_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='name_change_used',
            field=models.BooleanField(
                default=False,
                help_text='Whether the student has already used their one name change.',
            ),
        ),
    ]
