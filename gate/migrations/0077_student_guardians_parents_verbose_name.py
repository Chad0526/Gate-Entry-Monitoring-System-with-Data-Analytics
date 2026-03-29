# Generated manually for guardians_parents label (Guardians / Parents)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0076_attendance_log_result_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='guardians_parents',
            field=models.CharField(
                blank=True,
                help_text='Guardian(s) or parent(s) name(s)',
                max_length=255,
                verbose_name='Guardians / Parents',
            ),
        ),
    ]
