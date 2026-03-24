# Remove legacy Django auth Group "Guard" if it has no members (guard role removed from app).

from django.db import migrations


def remove_guard_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    g = Group.objects.filter(name__iexact='guard').first()
    if not g:
        return
    if User.objects.filter(groups=g).exists():
        return
    g.delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0062_migrate_guard_group_users_to_staff'),
    ]

    operations = [
        migrations.RunPython(remove_guard_group, noop_reverse),
    ]
