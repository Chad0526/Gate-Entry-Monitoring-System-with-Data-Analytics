# Student phone vs emergency contact labels

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0077_student_guardians_parents_verbose_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='contact_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='Your contact number'),
        ),
        migrations.AlterField(
            model_name='student',
            name='guardian_contact',
            field=models.CharField(
                blank=True,
                help_text='Emergency contact number (guardian).',
                max_length=20,
                verbose_name='Contact number',
            ),
        ),
    ]
