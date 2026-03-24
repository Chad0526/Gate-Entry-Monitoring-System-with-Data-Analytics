# Force-remove legacy auth Group "Guard" (any casing): move members to Staff, then delete.
# 0063 only deleted Guard when empty; this migration always clears and removes the group.

from django.db import migrations


def remove_guard_group_final(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')

    guard = Group.objects.filter(name__iexact='guard').first()
    if not guard:
        return

    staff = Group.objects.filter(name__iexact='staff').first()
    if not staff:
        staff = Group.objects.create(name='Staff')

    for user in User.objects.filter(groups=guard).iterator():
        user.groups.add(staff)
        user.groups.remove(guard)

    guard.delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0065_remove_load_slips_and_require_load_slip'),
    ]

    operations = [
        migrations.RunPython(remove_guard_group_final, noop_reverse),
    ]
