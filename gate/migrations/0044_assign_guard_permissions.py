# Assign gate custom permissions to Guard group (for role-based access)
from django.db import migrations


def assign_guard_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    guard_group, _ = Group.objects.get_or_create(name='Guard')
    perms = Permission.objects.filter(
        content_type__app_label='gate',
        content_type__model='gateentry',
        codename__in=['can_scan', 'can_view_entries', 'can_record_early_out', 'can_report_proxy'],
    )
    guard_group.permissions.add(*perms)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0043_guard_shift_and_gate_entry_audit'),
        ('auth', '0011_update_proxy_permissions'),
    ]

    operations = [
        migrations.RunPython(assign_guard_permissions, noop),
    ]
