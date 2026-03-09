# Add Supervisor role group (Gate Supervisor: reports, export, audit, guard activity; no students/users/events)

from django.db import migrations


def add_supervisor_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Supervisor')


def remove_supervisor_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Supervisor').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0045_add_student_signature'),
    ]

    operations = [
        migrations.RunPython(add_supervisor_group, remove_supervisor_group),
    ]
