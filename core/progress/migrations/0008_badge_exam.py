import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0009_exam_is_trial'),
        ('progress', '0007_rank_image_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='badge',
            name='exam',
            field=models.ForeignKey(
                blank=True,
                help_text='Optional. Limit this badge to one exam; leave blank to award it for every exam.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='badges',
                to='exams.exam',
            ),
        ),
    ]
