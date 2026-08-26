from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0004_module_has_lessons_alter_module_has_exams'),
    ]

    operations = [
        migrations.AddField(
            model_name='module',
            name='image_url',
            field=models.URLField(blank=True, help_text='Public URL of the module icon image.'),
        ),
    ]
