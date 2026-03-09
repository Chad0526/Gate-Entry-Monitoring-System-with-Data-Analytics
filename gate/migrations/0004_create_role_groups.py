# Generated migration - create role groups for RBAC

from django.db import migrations


def create_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in ('Admin', 'Faculty', 'Staff', 'Guard'):
        Group.objects.get_or_create(name=name)


def remove_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=('Admin', 'Faculty', 'Staff', 'Guard')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0003_gate_access_attendance_models'),
    ]

    operations = [
        migrations.RunPython(create_role_groups, remove_role_groups),
    ]
