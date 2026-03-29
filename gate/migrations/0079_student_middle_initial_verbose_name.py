# Student middle name field label -> Middle Initial

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0078_student_guardian_contact_verbose_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='middle_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Middle Initial'),
        ),
    ]
