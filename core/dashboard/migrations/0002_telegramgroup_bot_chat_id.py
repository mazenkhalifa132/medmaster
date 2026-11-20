from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_telegramgroup'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramgroup',
            name='bot_chat_id',
            field=models.CharField(
                blank=True,
                help_text='Telegram numeric chat ID or public @username. The bot must be able to post there.',
                max_length=128,
            ),
        ),
    ]
