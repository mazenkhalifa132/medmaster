from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0005_module_image_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='module',
            name='icon_class',
        ),
        migrations.AlterField(
            model_name='module',
            name='image_url',
            field=models.URLField(help_text='Public URL of the module icon image.'),
        ),
    ]
