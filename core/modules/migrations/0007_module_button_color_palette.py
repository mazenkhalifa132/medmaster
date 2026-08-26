from django.db import migrations, models
from django.core.validators import RegexValidator


BOOTSTRAP_COLORS = {
    'primary': '#0d6efd',
    'secondary': '#6c757d',
    'success': '#198754',
    'danger': '#dc3545',
    'warning': '#ffc107',
    'info': '#0dcaf0',
    'light': '#f8f9fa',
    'dark': '#212529',
}


def convert_button_colors(apps, schema_editor):
    Module = apps.get_model('modules', 'Module')
    for old_color, hex_color in BOOTSTRAP_COLORS.items():
        Module.objects.filter(btn_color=old_color).update(btn_color=hex_color)


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0006_remove_module_icon_class_require_image_url'),
    ]

    operations = [
        migrations.RunPython(convert_button_colors, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='module',
            name='btn_color',
            field=models.CharField(
                default='#3b82f6',
                max_length=7,
                validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color, for example #3b82f6.')],
                verbose_name='Button color',
            ),
        ),
    ]
