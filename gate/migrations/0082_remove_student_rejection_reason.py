# Remove Student.rejection_reason (field dropped from model).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0081_student_sex_male_female_only'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='rejection_reason',
        ),
    ]
