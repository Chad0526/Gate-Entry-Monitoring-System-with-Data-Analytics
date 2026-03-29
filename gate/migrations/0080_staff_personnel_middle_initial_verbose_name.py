# StaffPersonnelProfile middle_name field label -> Middle Initial

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0079_student_middle_initial_verbose_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staffpersonnelprofile',
            name='middle_name',
            field=models.CharField(blank=True, max_length=100, verbose_name='Middle Initial'),
        ),
    ]
