from django.db import migrations


def remove_supervisor_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    for g in Group.objects.filter(name__iexact='supervisor'):
        for u in User.objects.filter(groups=g):
            u.groups.remove(g)
        g.delete()


def recreate_supervisor_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Supervisor')


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0087_student_account_status_two_states'),
    ]

    operations = [
        migrations.RunPython(remove_supervisor_group, recreate_supervisor_group),
    ]
