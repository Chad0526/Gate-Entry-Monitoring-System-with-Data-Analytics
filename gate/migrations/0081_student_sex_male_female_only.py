# Generated manually: restrict sex to Male/Female; clear legacy OTHER/PREFER_NOT.

from django.db import migrations, models


def clear_legacy_sex(apps, schema_editor):
    Student = apps.get_model('gate', 'Student')
    StaffPersonnelProfile = apps.get_model('gate', 'StaffPersonnelProfile')
    Student.objects.filter(sex__in=['OTHER', 'PREFER_NOT']).update(sex='')
    StaffPersonnelProfile.objects.filter(sex__in=['OTHER', 'PREFER_NOT']).update(sex='')


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0080_staff_personnel_middle_initial_verbose_name'),
    ]

    operations = [
        migrations.RunPython(clear_legacy_sex, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='student',
            name='sex',
            field=models.CharField(
                blank=True,
                choices=[('MALE', 'Male'), ('FEMALE', 'Female')],
                help_text='Sex/Gender',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='staffpersonnelprofile',
            name='sex',
            field=models.CharField(
                blank=True,
                choices=[('MALE', 'Male'), ('FEMALE', 'Female')],
                max_length=20,
            ),
        ),
    ]
